from sqlalchemy import Column, Integer, String
from sqlalchemy.orm import relationship

from src.devaito.db.session import Base

from . import product_color_association


class Color(Base):
    __tablename__ = "agent_vw_com_colors"

    id = Column(Integer, primary_key=True)
    name = Column(String)

    def __repr__(self):
        return f"<Color(id={self.id}, name='{self.name}')>"

    products = relationship(
        "Product", secondary=product_color_association, back_populates="colors"
    )

    def to_dict(self):
        return {"id": self.id, "name": self.name, "test_test": "dad"}
