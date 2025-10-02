from sqlalchemy import JSON, Column, Integer, Numeric, String

from src.devaito.db.session import Base
from src.devaito.schemas.products import BasicVariantProductDetailDict


class BasicVariantProductDetail(Base):
    __tablename__ = "agent_vw_basic_variant_products_details_master"

    product_id = Column(Integer, primary_key=True)
    product_name = Column(String, nullable=False)
    product_description = Column(String, nullable=False)
    product_permalink = Column(String, nullable=False)
    brand_id = Column(Integer, nullable=True)
    brand_name = Column(String, nullable=True)
    categories = Column(JSON, nullable=False)
    variant = Column(String, nullable=True)
    price = Column(Numeric, nullable=True)
    quantity = Column(Integer, nullable=True)
    has_discount = Column(Integer, nullable=True)
    discount_type_name = Column(String, nullable=True)
    discount_label = Column(String, nullable=True)
    discount_amount = Column(Numeric, nullable=True)
    colors = Column(JSON, nullable=True)
    has_variant = Column(Integer, nullable=False)
    variants = Column(JSON, nullable=True)

    def __repr__(self):
        return f"<BasicVariantProductDetail(product_id={self.product_id}, product_name='{self.product_name}')>"

    def to_dict(self) -> BasicVariantProductDetailDict:
        return {
            "product_id": self.product_id,
            "product_name": self.product_name,
            "product_description": self.product_description,
            "product_permalink": self.product_permalink,
            "brand_id": self.brand_id,
            "brand_name": self.brand_name,
            "categories": self.categories,
            "variant": self.variant,
            "price": float(self.price) if self.price is not None else None,
            "quantity": self.quantity,
            "has_discount": self.has_discount,
            "discount_type_name": self.discount_type_name,
            "discount_label": self.discount_label,
            "discount_amount": (
                float(self.discount_amount)
                if self.discount_amount is not None
                else None
            ),
            "colors": self.colors,
            "has_variant": self.has_variant,
            "variants": self.variants,
        }
