import logging
from os import getenv

from dotenv import load_dotenv

load_dotenv(override=True)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class Config:
    """Application configuration with vector database settings"""

    # API Keys
    OPENAI_API_KEY = getenv("OPENAI_API_KEY")

    # Voice Settings
    VOICE_MODEL = "alloy"
    REALTIME_MODEL = "gpt-4o-mini-realtime-preview"
    STT_MODEL = "whisper-1"

    # Session Settings
    RPC_TIMEOUT = 10.0
    MAX_CONVERSATION_HISTORY = 50

    # Default Values
    DEFAULT_WEBSITE_NAME = "Our Website"
    DEFAULT_WEBSITE_DESCRIPTION = (
        "This is a helpful website where you can find great products and information."
    )

    # Vector Database Settings
    CHROMA_PERSIST_DIRECTORY: str | None = (
        None  # we will take it from website_name that mehdi passes with token metadata
    )
    CHROMA_COLLECTION_NAME = getenv("CHROMA_COLLECTION_NAME", "products")

    # Embedding Settings
    EMBEDDING_MODEL = getenv(
        "EMBEDDING_MODEL", "text-embedding-3-large"
    )  # Changed to cheaper model
    EMBEDDING_BATCH_SIZE = int(getenv("EMBEDDING_BATCH_SIZE", "100"))

    # API Endpoints
    PRODUCTS_API_ENDPOINT = "/ai-agent/vectore-save-products"

    # Cache Settings
    CACHE_TTL_SECONDS = int(
        getenv("CACHE_TTL_SECONDS", "3600")
    )  # 1 hour cache for product details
    MAX_CACHE_SIZE = int(
        getenv("MAX_CACHE_SIZE", "1000")
    )  # Maximum number of cached product details

    # Request Settings
    REQUEST_TIMEOUT = float(
        getenv("REQUEST_TIMEOUT", "10.0")
    )  # Timeout for API requests
    MAX_RETRIES = int(getenv("MAX_RETRIES", "3"))  # Maximum retries for failed requests

    # FastAPI Settings (for update endpoint)
    FASTAPI_PORT = int(getenv("FASTAPI_PORT", "8001"))
    FASTAPI_HOST = getenv("FASTAPI_HOST", "0.0.0.0")

    @classmethod
    def validate(cls):
        """Validate required configuration"""
        if not cls.OPENAI_API_KEY:
            raise ValueError("OPENAI_API_KEY is required for both voice and embeddings")

        logger.info("✅ Configuration validated successfully")
        logger.info(f"📦 ChromaDB persist directory: {cls.CHROMA_PERSIST_DIRECTORY}")
        logger.info(f"🔍 Embedding model: {cls.EMBEDDING_MODEL}")
        logger.info(f"⏰ Cache TTL: {cls.CACHE_TTL_SECONDS} seconds")
        logger.info(f"🔄 Max retries: {cls.MAX_RETRIES}")

        return True
