import asyncio
import logging

from src.core.config import Config
from src.data.vector_store import VectorStore, sanitize_add_parent_dir
from src.devaito.schemas.products import ProductForVectorDict
from src.devaito.services.products import get_all_products_for_vectors
from src.schemas.products import VectorProductFormat

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def transform_product_to_vector_format(
    product: ProductForVectorDict, hostname: str
) -> VectorProductFormat:
    """
    Transform database product to vector store format.

    Args:
        product: Product from database
        hostname: Website hostname

    Returns:
        Product formatted for vector store
    """
    # Build searchable document text
    document = f"{product['product_name']} - {product['product_description']}"

    # Extract category names
    categories = [cat["name"] for cat in product.get("categories", [])]

    # Determine product type
    if product["has_options"] == 1:
        product_type = "customizable"
    elif product["has_variant"] == 1:
        product_type = "variant"
    else:
        product_type = "basic"

    # Build URLs
    redirect_url = f"https://{hostname}/product/{product['product_permalink']}"

    return {
        "id": str(product["product_id"]),
        "document": document,
        "metadata": {
            "categories": categories,
            "brand": product.get("brand_name") or "",
            "product_type": product_type,
            "redirect_url": redirect_url,
        },
    }


async def sync_products_to_vector_store(
    database_name: str, clear_existing: bool = False, hostname: str = None
) -> dict:
    """
    Fetch products from database and sync to vector store.

    Args:
        database_name: Tenant identifier
        clear_existing: Whether to clear existing products first
        hostname: Website hostname

    Returns:
        Dict with sync results
    """
    try:
        logger.info(f"Starting sync for tenant: {database_name}")

        # Step 1: Fetch products from database
        logger.info("Fetching products from database...")
        db_products = await get_all_products_for_vectors(database_name)

        if not db_products:
            logger.warning("No products found in database")
            return {"success": False, "error": "No products found in database"}

        logger.info(f"Retrieved {len(db_products)} products from database")

        # Step 2: Transform products to vector format
        logger.info("Transforming products...")
        vector_products = [
            transform_product_to_vector_format(product, hostname=hostname)
            for product in db_products
        ]

        # Step 3: Initialize vector store
        logger.info("Initializing vector store...")
        persist_directory = sanitize_add_parent_dir(database_name)
        vector_store = VectorStore(
            collection_name=Config.CHROMA_COLLECTION_NAME,
            persist_directory=persist_directory,
            openai_api_key=Config.OPENAI_API_KEY,
        )

        # Step 4: Clear if requested
        if clear_existing:
            logger.info("Clearing existing products...")
            vector_store.clear_collection()

        # Step 5: Add products to vector store
        logger.info(f"Adding {len(vector_products)} products to vector store...")
        result = vector_store.add_products(vector_products)

        if result["success"]:
            logger.info(
                f"Sync completed: {result['added']} added, "
                f"{result['skipped']} skipped, "
                f"{result['total_in_db']} total in database"
            )
            return {
                "success": True,
                "products_fetched": len(db_products),
                "products_added": result["added"],
                "products_skipped": result["skipped"],
                "total_in_vector_db": result["total_in_db"],
            }
        else:
            logger.error(f"Failed to add products: {result.get('error')}")
            return {"success": False, "error": result.get("error", "Unknown error")}

    except Exception as e:
        logger.error(f"Error during sync: {e}")
        return {"success": False, "error": str(e)}


