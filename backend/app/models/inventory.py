"""Inventory change log — append-only audit trail for every stock movement."""

from datetime import datetime

from sqlalchemy import Column, Integer, String, DateTime, ForeignKey
from app.database import Base


class InventoryLog(Base):
    """Audit log recording every stock-in / stock-out / return / check adjustment."""

    __tablename__ = "inventory_log"

    id = Column(Integer, primary_key=True, autoincrement=True)
    product_id = Column(Integer, ForeignKey("product.id"), nullable=False, index=True, comment="Product FK")
    change_type = Column(
        String(20), nullable=False,
        comment="Movement type: 采购入库(purchase) / 销售出库(sale) / 采购退货入库 / 销售退货入库 / 盘点调整(check)"
    )
    change_quantity = Column(Integer, nullable=False, comment="Quantity delta (positive = in, negative = out)")
    after_quantity = Column(Integer, nullable=False, comment="Stock quantity after this movement (for audit)")
    reference_id = Column(Integer, comment="Related document ID")
    reference_type = Column(String(50), comment="Related document type: purchase_order / sale_order / check")
    created_at = Column(DateTime, default=datetime.now)
