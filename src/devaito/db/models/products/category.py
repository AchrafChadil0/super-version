from sqlalchemy import Column, Integer, String
from sqlalchemy.orm import relationship

from src.devaito.db.session import Base

from . import product_category_association


class Category(Base):
    __tablename__ = "agent_vw_com_categories"

    id = Column(Integer, primary_key=True)
    name = Column(String)
    permalink = Column(String, nullable=False)
    products = relationship(
        "Product",
        secondary=product_category_association,
        back_populates="categories",
    )

    def __repr__(self):
        return f"<Category(id={self.id}, name='{self.name}', permalink='{self.permalink}')>"

    def to_dict(self):
        return {"id": self.id, "name": self.name, "permalink": self.permalink}
