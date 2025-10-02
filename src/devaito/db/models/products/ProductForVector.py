from sqlalchemy import Column, Integer, String, JSON
from src.devaito.schemas.products import ProductForVectorDict
from src.devaito.db.session import Base


class ProductForVector(Base):
    __tablename__ = "agent_vw_products_for_vector_master"

    product_id = Column(Integer, primary_key=True)
    product_name = Column(String, nullable=False)
    product_description = Column(String, nullable=False)
    product_permalink = Column(String, nullable=False)
    has_options = Column(Integer, nullable=False)
    has_variant = Column(Integer, nullable=False)
    brand_id = Column(Integer, nullable=True)
    brand_name = Column(String, nullable=True)
    categories = Column(JSON, nullable=False)

    def __repr__(self):
        return f"<ProductForVector(product_id={self.product_id}, product_name='{self.product_name}')>"

    def to_dict(self) -> ProductForVectorDict:
        return {
            "product_id": self.product_id,
            "product_name": self.product_name,
            "product_description": self.product_description,
            "product_permalink": self.product_permalink,
            "has_options": self.has_options,
            "has_variant": self.has_variant,
            "brand_id": self.brand_id,
            "brand_name": self.brand_name,
            "categories": self.categories
        }