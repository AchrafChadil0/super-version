from sqlalchemy import Column, ForeignKey, Integer, Table

from src.devaito.db.session import Base

product_color_association = Table(
    "agent_vw_com_has_colors",
    Base.metadata,
    Column("id", Integer, primary_key=True),
    Column(
        "product_id", Integer, ForeignKey("agent_vw_com_products.id"), nullable=False
    ),
    Column("color_id", Integer, ForeignKey("agent_vw_com_colors.id"), nullable=False),
)

product_category_association = Table(
    "agent_vw_com_has_categories",
    Base.metadata,
    Column("id", Integer, primary_key=True),
    Column(
        "product_id", Integer, ForeignKey("agent_vw_com_products.id"), nullable=False
    ),
    Column(
        "category_id", Integer, ForeignKey("agent_vw_com_categories.id"), nullable=False
    ),
)
