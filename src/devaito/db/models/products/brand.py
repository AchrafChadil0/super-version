from sqlalchemy import Column, Integer, String
from sqlalchemy.ext.hybrid import hybrid_property

from src.devaito.db.session import Base


class Brand(Base):
    __tablename__ = "agent_vw_com_brands"

    id = Column(Integer, primary_key=True)
    name = Column(String(255), nullable=False)
    status = Column(Integer, nullable=False)  # 1 = active, 2 = inactive

    @hybrid_property
    def is_active(self) -> bool:
        """Return True if brand is active (status == 1)."""
        return self.status == 1

    @is_active.expression
    def is_active(cls):
        """SQL expression for filtering active brands."""
        return cls.status == 1

    def __repr__(self):
        return f"<Brand(id={self.id}, name='{self.name}', is_active={self.is_active})>"

    def to_dict(self):
        return {"id": self.id, "name": self.name, "is_active": self.is_active}
