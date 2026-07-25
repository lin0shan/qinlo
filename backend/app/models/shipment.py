from datetime import datetime

from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Text
from app.database import Base


class Shipment(Base):
    """Shipping record (independent table, supports split/partial shipments)."""

    __tablename__ = "shipment"

    id = Column(Integer, primary_key=True, autoincrement=True)
    sale_order_id = Column(Integer, ForeignKey("sale_order.id"), nullable=False, comment="Sale order FK")
    express_company = Column(String(50), comment="Courier company (SF/ZTO/YTO/Yunda/EMS/Other)")
    express_no = Column(String(100), comment="Tracking number")
    ship_status = Column(String(20), default="未发货", comment="Status: 未发货(pending)/已发货(shipped)/已签收(delivered)/已退货(returned)")
    receiver_name = Column(String(100), comment="Recipient name")
    receiver_phone = Column(String(30), comment="Recipient phone")
    receiver_address = Column(Text, comment="Recipient address")
    remark = Column(Text, comment="Notes")
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)
