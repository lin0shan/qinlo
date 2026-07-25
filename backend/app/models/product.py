"""Product model — core entity for inventory items."""

from datetime import datetime

from sqlalchemy import Column, Integer, String, Float, DateTime, Enum as SAEnum, Text
from app.database import Base
import enum


class ProductCategory(str, enum.Enum):
    SKINCARE = "护肤"   # e.g. toner, serum, moisturizer
    MAKEUP = "彩妆"     # e.g. lipstick, foundation, eyeshadow
    FRAGRANCE = "香水"   # perfume / cologne
    TOOL = "工具"        # brushes, sponges, applicators
    OTHER = "其他"        # other / miscellaneous


class ProductUnit(str, enum.Enum):
    BOTTLE = "瓶"
    BOX = "盒"
    TUBE = "支"
    PIECE = "片"
    PIECE_GE = "个"


class ProductStatus(str, enum.Enum):
    ACTIVE = "在售"
    INACTIVE = "停售"


class Product(Base):
    __tablename__ = "product"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(200), nullable=False, comment="Product name")
    barcode = Column(String(50), unique=True, comment="Barcode (Code128)")
    sku_code = Column(String(20), unique=True, comment="Internal SKU code (e.g. HLN-0001)")
    spec = Column(String(100), comment="Specification (e.g. 30ml / 50g)")
    brand = Column(String(50), default="", comment="Brand name")
    category = Column(String(20), nullable=False, default=ProductCategory.OTHER.value, comment="Category")
    unit = Column(String(10), nullable=False, default=ProductUnit.PIECE_GE.value, comment="Unit of measure")
    image_url = Column(String(500), comment="Image path (uploads/)")

    cost_price = Column(Float, nullable=False, default=0, comment="Cost price")
    retail_price = Column(Float, nullable=False, default=0, comment="Retail price")
    wholesale_price = Column(Float, default=0, comment="Wholesale price")

    current_stock = Column(Integer, default=0, comment="Current stock (redundant, synced from inventory_log)")
    safety_stock = Column(Integer, default=10, comment="Safety stock threshold for low-stock alert")
    status = Column(String(10), nullable=False, default=ProductStatus.ACTIVE.value, comment="Status: ACTIVE / INACTIVE")
    remark = Column(Text, comment="Notes")

    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)
