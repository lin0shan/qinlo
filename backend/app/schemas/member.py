from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime


class MemberCreate(BaseModel):
    name: str = Field(..., max_length=100)
    phone: str = Field(..., max_length=20)
    gender: Optional[str] = Field(None, max_length=10)
    birthday: Optional[str] = Field(None, max_length=20)
    skin_type: Optional[str] = Field(None, max_length=20)
    tags: Optional[str] = Field(None, max_length=200)
    remark: Optional[str] = None


class MemberUpdate(BaseModel):
    name: Optional[str] = Field(None, max_length=100)
    phone: Optional[str] = Field(None, max_length=20)
    gender: Optional[str] = Field(None, max_length=10)
    birthday: Optional[str] = Field(None, max_length=20)
    skin_type: Optional[str] = Field(None, max_length=20)
    tags: Optional[str] = Field(None, max_length=200)
    remark: Optional[str] = None


class PointAdjust(BaseModel):
    amount: int = Field(..., description="积分变化量，正数为增加，负数为扣减")
    brand: str = Field(..., max_length=50, description="品牌名称")
    remark: Optional[str] = None


class MemberResponse(BaseModel):
    id: int
    name: str
    phone: str
    gender: Optional[str]
    birthday: Optional[str]
    skin_type: Optional[str]
    tags: Optional[str]
    total_spent: float
    points: int
    brand_points: dict = {}
    remark: Optional[str]
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


class MemberDetailResponse(MemberResponse):
    orders: List[dict] = []


# ==================== Batch Operations ====================

class BatchPointsRequest(BaseModel):
    member_ids: List[int] = Field(..., min_length=1, description="List of member IDs")
    brand: str = Field(..., max_length=50, description="品牌名称")
    amount: int = Field(..., description="积分变化量（正数增加，负数扣减）")
    remark: Optional[str] = None


class CouponCreate(BaseModel):
    member_id: int
    brand: str = Field(..., max_length=50)
    coupon_name: str = Field(..., max_length=100)
    product_id: Optional[int] = None
    expires_at: str = Field(..., description="Expiration date, ISO format e.g. 2026-12-31")
    remark: Optional[str] = None


class BatchCouponRequest(BaseModel):
    member_ids: List[int] = Field(..., min_length=1, description="List of member IDs")
    brand: str = Field(..., max_length=50, description="品牌名称")
    coupon_name: str = Field(..., max_length=100, description="兑换券名称")
    product_id: Optional[int] = None
    expires_at: str = Field(..., description="Expiration date, ISO format e.g. 2026-12-31")
    remark: Optional[str] = None


class CouponResponse(BaseModel):
    id: int
    member_id: int
    member_name: str
    member_phone: str
    brand: str
    coupon_name: str
    product_id: Optional[int] = None
    product_name: Optional[str] = None
    status: str
    expires_at: Optional[datetime] = None
    used_at: Optional[datetime] = None
    remark: Optional[str] = None
    created_at: Optional[datetime] = None

    model_config = {"from_attributes": True}
