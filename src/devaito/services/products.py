from sqlalchemy import text

from src.devaito.config.cache_config import tenant_cached
from src.devaito.db.models.products import Category
from src.devaito.db.session import get_async_session
from src.devaito.repositories.products import (
    get_all_products_for_vector,
    get_basic_single_product_detail_by_id,
    get_basic_variant_product_detail_by_id,
    get_customizable_product_detail_by_id,
    get_product_by_id,
    get_product_for_vector_by_id,
    get_all_categories
)
from src.devaito.schemas.products import (
    BasicSingleProductDetailDict,
    BasicVariantProductDetailDict,
    CustomizableProductDetailDict,
    ProductDict,
    ProductForVectorDict,
)


async def warm_up_db(tenant_id: str):
    """Warm up database connection for a tenant."""
    async with get_async_session(tenant_id) as db:
        await db.execute(text("SELECT 1"))


@tenant_cached(ttl=300)
async def get_product(
    tenant_id: str,
    product_id: int,
    load_colors: bool = True,
    load_categories: bool = True,
) -> ProductDict:
    async with get_async_session(tenant_id) as db:
        product = await get_product_by_id(
            db, product_id, load_colors=load_colors, load_categories=load_categories
        )
        # Convert to list of dicts (or whatever serializable format)
        return product.to_dict()


@tenant_cached(ttl=300)
async def get_basic_single_product_detail(
    tenant_id: str,
    product_id: int,
) -> BasicSingleProductDetailDict | None:
    """Get basic single product detail by product ID.

    Args:
        tenant_id: The tenant identifier
        product_id: The product ID

    Returns:
        Dictionary with basic single product detail info, or None if not found
    """
    async with get_async_session(tenant_id) as db:
        product = await get_basic_single_product_detail_by_id(db, product_id)
        return product.to_dict() if product else None


@tenant_cached(ttl=300)
async def get_basic_variant_product_detail(
    tenant_id: str,
    product_id: int,
) -> BasicVariantProductDetailDict | None:
    """Get basic variant product detail by product ID.

    Args:
        tenant_id: The tenant identifier
        product_id: The product ID

    Returns:
        Dictionary with basic variant product detail info, or None if not found
    """
    async with get_async_session(tenant_id) as db:
        product = await get_basic_variant_product_detail_by_id(db, product_id)
        return product.to_dict() if product else None


@tenant_cached(ttl=300)
async def get_customizable_product_detail(
    tenant_id: str,
    product_id: int,
) -> CustomizableProductDetailDict | None:
    """Get customizable product detail by product ID.

    Args:
        tenant_id: The tenant identifier
        product_id: The product ID

    Returns:
        Dictionary with customizable product detail info, or None if not found
    """
    async with get_async_session(tenant_id) as db:
        product = await get_customizable_product_detail_by_id(db, product_id)
        return product.to_dict() if product else None


@tenant_cached(ttl=300)
async def get_product_for_vector(
    tenant_id: str,
    product_id: int,
) -> ProductForVectorDict | None:
    """Get product for vector by product ID.

    Args:
        tenant_id: The tenant identifier
        product_id: The product ID

    Returns:
        Dictionary with product info for vector operations, or None if not found
    """
    async with get_async_session(tenant_id) as db:
        product = await get_product_for_vector_by_id(db, product_id)
        return product.to_dict() if product else None


async def get_all_products_for_vectors(
    tenant_id: str,
) -> list[ProductForVectorDict]:
    """Get all products for vector operations.

    Args:
        tenant_id: The tenant identifier

    Returns:
        List of dictionaries with product info for vector operations
    """
    async with get_async_session(tenant_id) as db:
        products = await get_all_products_for_vector(db)
        return [product.to_dict() for product in products]

@tenant_cached(ttl=1000)
async def get_tenant_categories(
    tenant_id: str,
)->list[Category]:
    """Get product for vector by product ID.
    Args:
        tenant_id: The tenant identifier

    Returns:
        Dictionary with category info for vector operations, or Empty list if not found
    """
    async with get_async_session(tenant_id) as db:
        categories = await get_all_categories(db)
        return [category.to_dict() for category in categories]
