"""Member (CRM) models: members, brand-level points, and redemption vouchers."""

from datetime import datetime

from sqlalchemy import Column, Integer, String, Float, DateTime, Text, ForeignKey, UniqueConstraint
from app.database import Base


class Member(Base):
    __tablename__ = "member"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(100), nullable=False, comment="Member name")
    phone = Column(String(20), unique=True, nullable=False, comment="Phone number (unique identifier)")
    gender = Column(String(10), comment="Gender")
    birthday = Column(String(20), comment="Birthday (string format)")
    skin_type = Column(String(20), comment="Skin type: dry / oily / combination / sensitive")
    tags = Column(String(200), comment="Tags (comma-separated)")
    total_spent = Column(Float, default=0, comment="Cumulative spending")
    points = Column(Integer, default=0, comment="Total points (sum across all brands)")
    remark = Column(Text, comment="Notes")
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)


class MemberPoints(Base):
    __tablename__ = "member_points"

    id = Column(Integer, primary_key=True, autoincrement=True)
    member_id = Column(Integer, ForeignKey("member.id"), nullable=False, comment="Member FK")
    brand = Column(String(50), nullable=False, comment="Brand name")
    points = Column(Integer, default=0, comment="Points for this brand")
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)

    __table_args__ = (UniqueConstraint("member_id", "brand", name="uq_member_brand"),)


class MemberCoupon(Base):
    __tablename__ = "member_coupon"

    id = Column(Integer, primary_key=True, autoincrement=True)
    member_id = Column(Integer, ForeignKey("member.id"), nullable=False, comment="Member FK")
    brand = Column(String(50), nullable=False, comment="Brand name")
    coupon_name = Column(String(100), nullable=False, comment="Coupon / voucher name")
    product_id = Column(Integer, ForeignKey("product.id"), nullable=True, comment="Linked product FK (optional)")
    status = Column(String(20), default="有效", comment="Status: 有效(active) / 已兑换(redeemed) / 已过期(expired)")
    expires_at = Column(DateTime, nullable=False, comment="Expiration time")
    used_at = Column(DateTime, nullable=True, comment="When the coupon was redeemed")
    remark = Column(Text, comment="Notes")
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)
