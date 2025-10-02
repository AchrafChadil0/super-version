from sqlalchemy import Column, Integer, String, inspect
from sqlalchemy.ext.hybrid import hybrid_property
from sqlalchemy.orm import relationship

from src.devaito.db.session import Base

from . import Category, Color, product_category_association, product_color_association


class Product(Base):
    """don't use the product.colors, use product.get_colors(), using .colors direct will cause errors"""

    __tablename__ = "agent_vw_com_products"

    id = Column(Integer, primary_key=True)
    name = Column(String(255), nullable=False)
    description = Column(String, nullable=True)
    permalink = Column(String(255), nullable=False)
    brand = Column(Integer, nullable=True)

    has_options = Column(Integer, nullable=False)  # 0 = no, 1 = yes
    has_variant = Column(Integer, nullable=False)  # 1 = has variants, 2 = no variants

    # ⚠️ WARNING: Direct access to relationship attributes (e.g., `.colors`, `.categories`, etc.)
    #            triggers lazy loading and will FAIL if the related data was not eagerly loaded
    #            (e.g., if `load_colors=False` or the instance is detached).
    #            This raises `DetachedInstanceError` in sync contexts or `MissingGreenlet` in async contexts.
    #            ALWAYS use explicit accessor methods like `.get_colors()`, `.get_categories()`, etc.,
    #            which safely handle detached or unloaded states.
    #            See: https://sqlalche.me/e/20/bhk3
    colors = relationship(
        "Color",
        secondary=product_color_association,
        back_populates="products",
    )

    categories = relationship(
        "Category",
        secondary=product_category_association,
        back_populates="products",
    )
    # ----------------------------

    def get_colors(self) -> list[Color] | None:
        """Safely return colors if loaded, else None"""
        insp = inspect(self)
        if "colors" in insp.unloaded:
            return None
        return self.colors

    def get_categories(self) -> list[Category] | None:
        """Safely return categories if loaded, else None"""
        insp = inspect(self)
        if "categories" in insp.unloaded:
            return None
        return self.categories

    @hybrid_property
    def has_product_options(self) -> bool:
        return self.has_options == 1

    @has_product_options.expression
    def has_product_options(cls):
        return cls.has_options == 1

    @hybrid_property
    def has_variants(self) -> bool:
        return self.has_variant == 1

    @has_variants.expression
    def has_variants(cls):
        return cls.has_variant == 1

    def __repr__(self):
        return (
            f"<Product(id={self.id}, name='{self.name}', brand={self.brand}, "
            f"has_options={self.has_product_options}, has_variants={self.has_variants}, "
            f"colors={self._serialize_relationship('colors')},"
            f"categories={self._serialize_relationship('categories')}"
        )

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "brand": self.brand,
            "has_options": self.has_product_options,
            "has_variants": self.has_variants,
            "colors": self._serialize_relationship("colors"),
            "categories": self._serialize_relationship("categories"),
        }

    def _serialize_relationship(
        self, attr_name: str, fields: list[str] = None
    ) -> list[dict] | list:
        """
        Safely serialize a relationship if it's loaded.

        :param attr_name: Name of the relationship attribute (e.g., 'colors', 'categories')
        :param fields: List of field names to include (e.g., ['id', 'name']).
                       If None, calls .to_dict() on each item (recommended).
        :return: List of dicts if loaded and items exist, else [].
        """
        insp = inspect(self)
        if attr_name in insp.unloaded:
            return []

        rel = getattr(self, attr_name, [])
        if not rel:
            return []

        if fields is not None:
            # Fallback: extract specific fields (less flexible)
            return [
                {
                    field: getattr(item, field)
                    for field in fields
                    if hasattr(item, field)
                }
                for item in rel
            ]
        else:
            # Preferred: delegate to each model's .to_dict()
            return [item.to_dict() for item in rel if hasattr(item, "to_dict")]
