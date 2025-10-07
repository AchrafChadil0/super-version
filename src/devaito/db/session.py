# session.py
import logging
from contextlib import asynccontextmanager
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import declarative_base
from sqlalchemy.pool import NullPool

from src.devaito.config.database_config import (
    DEFAULT_POOL_CONFIG,
    TENANT_POOL_CONFIGS,
    DatabaseConfig,
    get_tenant_pool_config,
)

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)  # Set the logging level

# Create file handler
file_handler = logging.FileHandler("app.log")
file_handler.setLevel(logging.DEBUG)

# Create formatter and add it to the handler
formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
file_handler.setFormatter(formatter)

# Add the handler to the logger
logger.addHandler(file_handler)

database_config = DatabaseConfig()
_tenant_engines = {}


def get_tenant_tier(tenant_id: str) -> str:
    """
    Determine tenant tier based on tenant_id or configuration.
    This could be fetched from a database, configuration file, or API.
    """
    # Example logic - replace with your actual tier determination
    if tenant_id.startswith("premium_"):
        return "premium"
    elif tenant_id.startswith("free_"):
        return "free"
    elif tenant_id == "development" or tenant_id == "test":
        return "development"
    else:
        return "standard"


def get_pool_config_for_tenant(tenant_id: str) -> dict[str, Any]:
    """
    Get pool configuration for a specific tenant.
    Can be customized per tenant or use tier-based configs.
    """
    # Check if there's a specific override for this tenant
    # This could come from a database or API
    tenant_specific_config = get_tenant_pool_config(tenant_id)

    if tenant_specific_config:
        return tenant_specific_config

    # Otherwise, use tier-based configuration
    tier = get_tenant_tier(tenant_id)
    return TENANT_POOL_CONFIGS.get(tier, DEFAULT_POOL_CONFIG).copy()


def get_tenant_engine(tenant_id: str, pool_config: dict[str, Any] | None = None):
    """
    Get or create engine for specific tenant with custom pool configuration.

    Args:
        tenant_id: Unique identifier for the tenant
        pool_config: Optional custom pool configuration override
    """
    if tenant_id not in _tenant_engines:
        logger.info(f"Creating new engine for tenant: {tenant_id}")

        # Get pool configuration
        config = pool_config or get_pool_config_for_tenant(tenant_id)

        # Extract pool-specific settings
        pool_size = config.pop("pool_size", 5)
        max_overflow = config.pop("max_overflow", 10)
        pool_timeout = config.pop("pool_timeout", 30)
        pool_recycle = config.pop("pool_recycle", 3600)
        pool_pre_ping = config.pop("pool_pre_ping", True)

        # Determine if we should use NullPool for certain scenarios
        use_null_pool = config.pop("use_null_pool", False)

        database_url = database_config.get_database_url(tenant_id)

        # Log the pool configuration being used
        logger.info(
            f"Creating engine for tenant '{tenant_id}' with pool config: "
            f"size={pool_size}, max_overflow={max_overflow}, "
            f"timeout={pool_timeout}s, recycle={pool_recycle}s"
        )

        # Create engine with appropriate pooling
        if use_null_pool:
            # NullPool creates a new connection for each request
            # Useful for serverless or very low-traffic scenarios
            _tenant_engines[tenant_id] = create_async_engine(
                database_url,
                echo=(
                    database_config.debug_mode
                    if hasattr(database_config, "debug_mode")
                    else False
                ),
                poolclass=NullPool,
            )
        else:
            # QueuePool is the default and recommended for most scenarios
            _tenant_engines[tenant_id] = create_async_engine(
                database_url,
                echo=True,
                pool_size=pool_size,
                max_overflow=max_overflow,
                pool_timeout=pool_timeout,
                pool_recycle=pool_recycle,
                pool_pre_ping=pool_pre_ping,
                # Additional performance settings
                connect_args=(
                    {
                        "server_settings": {
                            "application_name": f"app_tenant_{tenant_id}",
                            "jit": "off",
                        },
                        "command_timeout": 60,
                    }
                    if database_url.startswith("postgresql")
                    else {}
                ),
            )

    return _tenant_engines[tenant_id]


def get_tenant_session_factory(tenant_id: str):
    """Get session factory for specific tenant"""
    engine = get_tenant_engine(tenant_id)
    return async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


Base = declarative_base()


@asynccontextmanager
async def get_async_session(tenant_id: str = "default"):
    """
    Get async session for specific tenant with automatic resource management.

    Args:
        tenant_id: The tenant identifier

    Yields:
        AsyncSession: Database session for the tenant

    Example:
        async with get_async_session("tenant_123") as session:
            result = await session.execute(select(User))
    """
    session_factory = get_tenant_session_factory(tenant_id)
    logger.debug(f"Active engines: {list(_tenant_engines.keys())}")

    async with session_factory() as session:
        try:
            yield session
        except Exception as e:
            logger.error(f"Database error for tenant {tenant_id}: {str(e)}")
            await session.rollback()
            raise
        finally:
            await session.close()


async def dispose_tenant_engine(tenant_id: str):
    """
    Dispose of a tenant's engine and remove it from cache.
    Useful for cleanup or when a tenant is deactivated.

    Args:
        tenant_id: The tenant identifier
    """
    if tenant_id in _tenant_engines:
        logger.info(f"Disposing engine for tenant: {tenant_id}")
        engine = _tenant_engines[tenant_id]
        await engine.dispose()
        del _tenant_engines[tenant_id]


async def dispose_all_engines():
    """
    Dispose all tenant engines.
    Should be called during application shutdown.
    """
    logger.info(f"Disposing all {len(_tenant_engines)} tenant engines")
    for tenant_id in list(_tenant_engines.keys()):
        await dispose_tenant_engine(tenant_id)


def get_engine_pool_status(tenant_id: str) -> dict[str, Any] | None:
    """
    Get current pool status for monitoring purposes.

    Args:
        tenant_id: The tenant identifier

    Returns:
        Dictionary with pool statistics or None if engine doesn't exist
    """
    if tenant_id not in _tenant_engines:
        return None

    engine = _tenant_engines[tenant_id]
    pool = engine.pool

    # This works for QueuePool, might need adjustment for other pool types
    if hasattr(pool, "size"):
        return {
            "tenant_id": tenant_id,
            "size": pool.size(),
            "checked_in": pool.checkedin(),
            "checked_out": pool.checkedout(),
            "overflow": pool.overflow(),
            "total": pool.checkedin() + pool.checkedout(),
        }
    return {"type": type(pool).__name__}


# Optional: Monitoring utilities
class PoolMonitor:
    """Helper class for monitoring connection pool usage"""

    @staticmethod
    def log_pool_stats():
        """Log current pool statistics for all tenants"""
        for tenant_id in _tenant_engines:
            stats = get_engine_pool_status(tenant_id)
            if stats:
                logger.info(f"Tenant {tenant_id} pool stats: {stats}")

    @staticmethod
    def get_pool_stats(tenant_id: str) -> dict[str, Any]:
        """Get pool statistics for all tenants"""
        return get_engine_pool_status(tenant_id=tenant_id)

    @staticmethod
    def get_all_pool_stats() -> dict[str, Any]:
        """Get pool statistics for all tenants"""
        return {
            tenant_id: get_engine_pool_status(tenant_id)
            for tenant_id in _tenant_engines
        }

    @staticmethod
    def check_pool_health(tenant_id: str) -> bool:
        """
        Check if a tenant's pool is healthy.

        Returns:
            True if healthy, False if potential issues detected
        """
        stats = get_engine_pool_status(tenant_id)
        if not stats or "checked_out" not in stats:
            return True

        config = get_pool_config_for_tenant(tenant_id)
        max_connections = config.get("pool_size", 5) + config.get("max_overflow", 10)

        # Check if we're near the connection limit
        if stats["total"] >= max_connections * 0.9:
            logger.warning(
                f"Tenant {tenant_id} approaching connection limit: "
                f"{stats['total']}/{max_connections}"
            )
            return False

        return True
