from typing import Optional, Any, Coroutine, Sequence

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload
from sqlalchemy.sql.base import ExecutableOption

from src.devaito.db.models.products import (
    BasicSingleProductDetail,
    BasicVariantProductDetail,
    Brand,
    Category,
    CustomizableProductDetail,
    Product,
    ProductForVector,
)


async def get_all_products(db: AsyncSession):
    pass


async def get_product_by_id(
    db: AsyncSession,
    product_id: int,
    load_categories: bool = True,
    load_colors: bool = True,
) -> Product:
    options: list[ExecutableOption] = []
    if load_categories:
        options.append(joinedload(Product.categories))  # Changed
    if load_colors:
        options.append(joinedload(Product.colors))  # Changed

    stmt = select(Product).options(*options).where(Product.id == product_id)
    result = await db.execute(stmt)
    product = result.unique().scalar_one_or_none()  # Added .unique()
    return product


async def get_all_categories(db: AsyncSession):
    result = await db.execute(select(Category))
    return result.scalars().all()


async def get_all_brands(db: AsyncSession):
    result = await db.execute(select(Brand))
    return result.scalars().all()


async def get_basic_single_product_detail_by_id(
    db: AsyncSession, product_id: int
) -> BasicSingleProductDetail | None:
    """Get basic single product detail by product ID."""
    stmt = select(BasicSingleProductDetail).where(
        BasicSingleProductDetail.product_id == product_id
    )
    result = await db.execute(stmt)
    return result.scalar_one_or_none()


async def get_basic_variant_product_detail_by_id(
    db: AsyncSession, product_id: int
) -> BasicVariantProductDetail | None:
    """Get basic variant product detail by product ID."""
    stmt = select(BasicVariantProductDetail).where(
        BasicVariantProductDetail.product_id == product_id
    )
    result = await db.execute(stmt)
    return result.scalar_one_or_none()


async def get_customizable_product_detail_by_id(
    db: AsyncSession, product_id: int
) -> CustomizableProductDetail | None:
    """Get customizable product detail by product ID."""
    stmt = select(CustomizableProductDetail).where(
        CustomizableProductDetail.product_id == product_id
    )
    result = await db.execute(stmt)
    return result.scalar_one_or_none()

async def get_product_for_vector_by_id(
    db: AsyncSession,
    product_id: int
) -> Optional[ProductForVector]:
    """Get product for vector by product ID."""
    stmt = select(ProductForVector).where(
        ProductForVector.product_id == product_id
    )
    result = await db.execute(stmt)
    return result.scalar_one_or_none()

async def get_all_products_for_vector(
    db: AsyncSession
) -> Sequence[ProductForVector]:
    """Get all products for vector."""
    stmt = select(ProductForVector)
    result = await db.execute(stmt)
    return result.scalars().all()
