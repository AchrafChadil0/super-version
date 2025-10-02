# cache_config.py
import os

import redis.asyncio as redis
from aiocache import Cache, cached
from aiocache.serializers import JsonSerializer
from dotenv import load_dotenv

from src.devaito.config.global_config import GlobalConfig

load_dotenv()

CACHE_CONFIG = {
    "endpoint": os.getenv("REDIS_HOST", "localhost"),
    "port": int(os.getenv("REDIS_PORT", 6379)),
    "db": int(os.getenv("REDIS_DB", 0)),
    "serializer": JsonSerializer(),
}
config = GlobalConfig()


class TenantCacheManager:
    def __init__(self):
        self._redis_client = None

    async def get_redis_client(self):
        """Get Redis client for direct operations"""
        if self._redis_client is None:
            self._redis_client = redis.Redis(
                host=CACHE_CONFIG["endpoint"],
                port=CACHE_CONFIG["port"],
                db=CACHE_CONFIG["db"],
                decode_responses=True,
            )
        return self._redis_client

    async def delete_tenant_cache(self, tenant_id: str, pattern: str = "*") -> int:
        """
        Delete all cache entries for a specific tenant

        Args:
            tenant_id: The tenant identifier
            pattern: Pattern to match keys (default: "*" for all)

        Returns:
            Number of keys deleted
        """
        client = await self.get_redis_client()
        search_pattern = f"{config.AGENT_CLIENT}:tenant:{tenant_id}:{pattern}"

        # Find all keys matching the pattern
        keys = await client.keys(search_pattern)

        if keys:
            # Delete all found keys
            deleted_count = await client.delete(*keys)
            return deleted_count

        return 0

    async def delete_cache_by_function(self, tenant_id: str, function_name: str) -> int:
        """
        Delete all cache entries for a specific function name regardless of arguments

        Args:
            tenant_id: The tenant identifier
            function_name: Name of the cached function

        Returns:
            Number of keys deleted
        """
        # Build pattern to match all keys for this function
        pattern = f"{config.AGENT_CLIENT}:tenant:{tenant_id}:{function_name}:*"

        client = await self.get_redis_client()

        # Find all matching keys
        keys = await client.keys(pattern)

        if not keys:
            return 0

        # Delete all matching keys
        deleted_count = await client.delete(*keys)

        return deleted_count

    async def list_tenant_cache_keys(
        self, tenant_id: str, pattern: str = "*"
    ) -> list[str]:
        """
        List all cache keys for a tenant

        Args:
            tenant_id: The tenant identifier
            pattern: Pattern to match keys

        Returns:
            List of cache keys
        """
        client = await self.get_redis_client()
        search_pattern = f"{config.AGENT_CLIENT}:tenant:{tenant_id}:{pattern}"
        keys = await client.keys(search_pattern)
        return keys

    async def get_cache_stats(self, tenant_id: str) -> dict:
        """
        Get cache statistics for a tenant

        Args:
            tenant_id: The tenant identifier

        Returns:
            Dictionary with cache statistics including estimated memory usage
        """
        client = await self.get_redis_client()
        keys = await self.list_tenant_cache_keys(tenant_id)

        stats = {
            "total_keys": len(keys),
            "keys_by_function": {},
            "memory_usage_estimate_bytes": 0,
            "memory_usage_estimate_mb": 0.0,
        }

        total_memory = 0
        for key in keys:
            # Extract function name from key
            parts = key.split(":")
            if len(parts) >= 4:
                func_name = parts[3]
                stats["keys_by_function"][func_name] = (
                    stats["keys_by_function"].get(func_name, 0) + 1
                )

            # Estimate memory usage for this key
            try:
                mem_bytes = await client.memory_usage(key)
                if mem_bytes is not None:
                    total_memory += mem_bytes
            except Exception:
                # Log or handle error if needed (e.g., key expired during scan)
                continue

        stats["memory_usage_estimate_bytes"] = total_memory
        stats["memory_usage_estimate_mb"] = round(total_memory / (1024 * 1024), 2)

        return stats

    async def close(self):
        """Close Redis connection"""
        if self._redis_client:
            await self._redis_client.close()


# Global cache manager instance
cache_manager = TenantCacheManager()


# Custom key builder for tenant isolation
def tenant_key_builder(func, *args, **kwargs):
    """Build cache key with tenant isolation"""
    tenant_id = kwargs.get("tenant_id", "default")

    # Remove tenant_id from kwargs copy for key generation
    cache_kwargs = {k: v for k, v in kwargs.items() if k != "tenant_id"}

    # Build base key from function name and args
    func_args = [str(arg) for arg in args]
    func_kwargs = [f"{k}={v}" for k, v in sorted(cache_kwargs.items())]
    base_key = f"{func.__name__}:{':'.join(func_args + func_kwargs)}"

    return f"{config.AGENT_CLIENT}:tenant:{tenant_id}:{base_key}"


# Convenient decorator
def tenant_cached(ttl: int = 300, cache=None, key_builder=None):
    """Tenant-aware caching decorator"""
    return cached(
        ttl=ttl,
        cache=Cache.REDIS,
        key_builder=key_builder or tenant_key_builder,
        **CACHE_CONFIG,
    )
