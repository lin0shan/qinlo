"""Purchase order and sale order models with item-level line items."""

from datetime import datetime

from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, Text
from sqlalchemy.orm import relationship
from app.database import Base


class PurchaseOrder(Base):
    __tablename__ = "purchase_order"

    id = Column(Integer, primary_key=True, autoincrement=True)
    supplier_id = Column(Integer, ForeignKey("supplier.id"), comment="Supplier FK")
    total_amount = Column(Float, nullable=False, default=0, comment="Total amount")
    status = Column(String(20), default="已完成", comment="Status: 已完成 / 已退货")
    remark = Column(Text, comment="Notes")
    created_at = Column(DateTime, default=datetime.now)

    supplier = relationship("Supplier", lazy="joined")
    items = relationship("PurchaseOrderItem", lazy="joined", cascade="all, delete-orphan")


class PurchaseOrderItem(Base):
    __tablename__ = "purchase_order_item"

    id = Column(Integer, primary_key=True, autoincrement=True)
    purchase_order_id = Column(Integer, ForeignKey("purchase_order.id"), nullable=False)
    product_id = Column(Integer, ForeignKey("product.id"), nullable=False)
    quantity = Column(Integer, nullable=False, comment="Purchase quantity")
    unit_price = Column(Float, nullable=False, comment="Unit price at purchase")

    product = relationship("Product", lazy="joined")


class SaleOrder(Base):
    __tablename__ = "sale_order"

    id = Column(Integer, primary_key=True, autoincrement=True)
    order_number = Column(String(20), unique=True, comment="Order number (e.g. 20260719001)")
    member_id = Column(Integer, ForeignKey("member.id"), nullable=True, comment="Member FK (nullable)")
    total_amount = Column(Float, nullable=False, default=0, comment="Gross total before discount")
    discount = Column(Float, default=0, comment="Discount amount")
    actual_amount = Column(Float, nullable=False, default=0, comment="Net amount received")
    status = Column(String(20), default="已完成", comment="Status: 已完成 / 已退货")
    remark = Column(Text, comment="Notes")
    created_at = Column(DateTime, default=datetime.now)

    member = relationship("Member", lazy="joined")
    items = relationship("SaleOrderItem", lazy="joined", cascade="all, delete-orphan")
    shipments = relationship("Shipment", lazy="joined", cascade="all, delete-orphan")


class SaleOrderItem(Base):
    __tablename__ = "sale_order_item"

    id = Column(Integer, primary_key=True, autoincrement=True)
    sale_order_id = Column(Integer, ForeignKey("sale_order.id"), nullable=False)
    product_id = Column(Integer, ForeignKey("product.id"), nullable=False)
    quantity = Column(Integer, nullable=False, comment="Sale quantity")
    unit_price = Column(Float, nullable=False, comment="Unit price at sale")

    product = relationship("Product", lazy="joined")
