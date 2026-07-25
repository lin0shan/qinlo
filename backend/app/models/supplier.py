"""Supplier model."""

from sqlalchemy import Column, Integer, String, Text
from app.database import Base


class Supplier(Base):
    __tablename__ = "supplier"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(200), nullable=False, comment="Supplier name")
    contact = Column(String(100), comment="Contact person")
    phone = Column(String(30), comment="Phone number")
    remark = Column(Text, comment="Notes")
