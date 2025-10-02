import os
from typing import Any
from urllib.parse import quote_plus

from dotenv import load_dotenv

# Default pool configuration
DEFAULT_POOL_CONFIG = {
    "pool_size": 5,  # Number of connections to maintain in pool
    "max_overflow": 10,  # Maximum overflow connections above pool_size
    "pool_timeout": 30,  # Seconds to wait before timing out
    "pool_recycle": 3600,  # Recycle connections after 1 hour
    "pool_pre_ping": True,  # Test connections before using
}


TENANT_POOL_CONFIGS = {
    # Premium tenants get more resources
    "premium": {
        "pool_size": 20,
        "max_overflow": 30,
        "pool_timeout": 30,
        "pool_recycle": 3600,
        "pool_pre_ping": True,
    },
    # Standard tenants get default resources
    "standard": DEFAULT_POOL_CONFIG.copy(),
    # Free tier tenants get minimal resources
    "free": {
        "pool_size": 2,
        "max_overflow": 3,
        "pool_timeout": 10,
        "pool_recycle": 1800,  # Recycle more frequently
        "pool_pre_ping": True,
    },
    # Development/testing environments
    "development": {
        "pool_size": 1,
        "max_overflow": 2,
        "pool_timeout": 5,
        "pool_recycle": 300,
        "pool_pre_ping": True,
    },
}


def get_tenant_pool_config(tenant_id: str) -> dict[str, Any] | None:
    """
    Get custom pool configuration for a specific tenant.

    Currently, returns None to indicate no per-tenant override exists.
    This method is a placeholder for future extension (e.g., fetching from DB).

    Args:
        tenant_id (str): The tenant identifier

    Returns:
        dict or None: Custom config if available, otherwise None
    """
    # TODO: In the future, you might fetch this from a database or API
    # Example:
    #   return self._fetch_from_tenant_settings(tenant_id)
    return None


class DatabaseConfig:
    def __init__(self, load_env: bool = True):
        """
        Initialize the database configuration.

        Args:
            load_env (bool): Whether to load environment variables from .env file
        """
        if load_env:
            load_dotenv()

        self.db_user = os.getenv("DB_USER", "root")
        self.db_password = os.getenv("DB_PASSWORD", "password")
        self.db_host = os.getenv("DB_HOST", "localhost")
        self.db_port = os.getenv("DB_PORT", "3309")
        self.db_name = os.getenv("DB_NAME", "your_database")
        self.agent_client = os.getenv("AGENT_CLIENT")

        # URL-encode the password to handle special characters
        pwd_quoted = quote_plus(self.db_password)
        self.database_url = f"mysql+aiomysql://{self.db_user}:{pwd_quoted}@{self.db_host}:{self.db_port}/"

    def get_database_url(self, tenant_id: str) -> str:
        """
        Get the complete database URL for a specific tenant.

        Args:
            tenant_id (str): The tenant identifier to append to the database URL

        Returns:
            str: Complete database URL with tenant ID

        Raises:
            ValueError: If DATABASE_URL or tenant_id is not present
        """
        if not self.database_url:
            raise ValueError("DATABASE_URL is not present")
        if not tenant_id:
            raise ValueError("TENANT_ID is not present")
        return f"{self.database_url}{tenant_id}"

    @property
    def base_url(self) -> str:
        """Get the base database URL without tenant ID."""
        return self.database_url

    def __repr__(self) -> str:
        """String representation of the database config (without exposing password)."""
        return f"DatabaseConfig(host={self.db_host}, port={self.db_port}, user={self.db_user})"
