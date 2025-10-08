# Add this import at the top
import logging

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, HttpUrl

from src.core.config import Config
from src.data.db_to_vector import sync_products_to_vector_store
from src.data.vector_store import VectorStore

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


# Add new request model
class SyncFromDatabaseRequest(BaseModel):
    database_name: str
    base_url: HttpUrl
    clear_existing: bool = False


class SyncFromDatabaseResponse(BaseModel):
    success: bool
    message: str
    products_fetched: int = 0
    products_added: int = 0
    products_skipped: int = 0
    total_in_vector_db: int = 0
    error: str | None = None


class HealthResponse(BaseModel):
    status: str
    vector_store_ready: bool
    openai_key_configured: bool


class ProductStatsResponse(BaseModel):
    total_products: int
    categories: list[str]
    brands: list[str]
    product_types: dict[str, int]
    last_update: str | None = None


app = FastAPI(
    title="LiveKit Agent Vector Store API",
    description="API for updating product data in the vector database",
    version="1.0.0",
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def get_vector_store_instance(database_name: str):
    """Create a new vector store instance for the specific website"""


    return VectorStore(
        collection_name=Config.CHROMA_COLLECTION_NAME,
        persist_directory=database_name,
        openai_api_key=Config.OPENAI_API_KEY,
    )


@app.get("/health", response_model=HealthResponse)
async def health_check():
    """Check if the API is healthy and ready"""
    try:
        return HealthResponse(
            status="healthy",
            vector_store_ready=True,
            openai_key_configured=bool(Config.OPENAI_API_KEY),
        )
    except Exception:
        return HealthResponse(
            status="unhealthy",
            vector_store_ready=False,
            openai_key_configured=bool(Config.OPENAI_API_KEY),
        )


@app.get("/stats", response_model=ProductStatsResponse)
async def get_product_stats(database_name: str):
    """Get current statistics about products in the vector store"""
    try:

        store = get_vector_store_instance(database_name)  # Create new instance
        stats = store.get_statistics()

        return ProductStatsResponse(
            total_products=stats.get("total_products", 0),
            categories=stats.get("categories", []),
            brands=stats.get("brands", []),
            product_types=stats.get("product_types", {}),
        )
    except Exception as e:
        logger.error(f"Error getting stats: {e}")
        raise HTTPException(status_code=500, detail=str(e)) from e


@app.delete("/clear-products")
async def clear_all_products(database_name: str):
    """Clear all products from the vector store"""
    try:

        store = get_vector_store_instance(database_name)  # Create new instance

        success = store.clear_collection()

        if success:
            return {"success": True, "message": "All products cleared successfully"}
        else:
            raise HTTPException(status_code=500, detail="Failed to clear products")
    except Exception as e:
        logger.error(f"Error clearing products: {e}")
        raise HTTPException(status_code=500, detail=str(e)) from e


# Add this new endpoint
@app.post("/sync-from-database", response_model=SyncFromDatabaseResponse)
async def sync_from_database(request: SyncFromDatabaseRequest):
    """
    Sync products from database to vector store

    Fetches products from the tenant's database and adds them to ChromaDB
    """
    try:
        logger.info(f"Starting database sync for tenant: {request.database_name}")

        # Run sync
        result = await sync_products_to_vector_store(
            database_name=request.database_name,
            base_url=str(request.base_url),
            clear_existing=request.clear_existing,
        )

        if result["success"]:
            return SyncFromDatabaseResponse(
                success=True,
                message=f"Successfully synced products for tenant {request.database_name}",
                products_fetched=result["products_fetched"],
                products_added=result["products_added"],
                products_skipped=result["products_skipped"],
                total_in_vector_db=result["total_in_vector_db"],
            )
        else:
            return SyncFromDatabaseResponse(
                success=False,
                message="Failed to sync products from database",
                error=result.get("error", "Unknown error"),
            )

    except Exception as e:
        logger.error(f"Error syncing from database: {e}")
        return SyncFromDatabaseResponse(
            success=False, message="Internal server error", error=str(e)
        )
