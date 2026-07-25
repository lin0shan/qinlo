from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime


# ===== Purchase Orders =====

class PurchaseOrderItemCreate(BaseModel):
    product_id: int
    quantity: int = Field(..., gt=0)
    unit_price: float = Field(..., ge=0)


class PurchaseOrderCreate(BaseModel):
    supplier_id: int
    items: List[PurchaseOrderItemCreate] = Field(..., min_length=1)
    remark: Optional[str] = None


class PurchaseOrderItemResponse(BaseModel):
    id: int
    product_id: int
    product_name: str = ""
    quantity: int
    unit_price: float

    model_config = {"from_attributes": True}


class PurchaseOrderResponse(BaseModel):
    id: int
    supplier_id: int
    supplier_name: str = ""
    total_amount: float
    status: str
    remark: Optional[str]
    items: List[PurchaseOrderItemResponse] = []
    created_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


# ===== Sale Orders =====

class SaleOrderItemCreate(BaseModel):
    product_id: int
    quantity: int = Field(..., gt=0)
    unit_price: float = Field(..., ge=0)


class SaleOrderCreate(BaseModel):
    member_id: Optional[int] = None
    items: List[SaleOrderItemCreate] = Field(..., min_length=1)
    discount: float = Field(default=0, ge=0)
    remark: Optional[str] = None


class SaleOrderItemResponse(BaseModel):
    id: int
    product_id: int
    product_name: str = ""
    quantity: int
    unit_price: float

    model_config = {"from_attributes": True}


class SaleOrderResponse(BaseModel):
    id: int
    order_number: Optional[str] = None
    member_id: Optional[int] = None
    member_name: Optional[str] = None
    total_amount: float
    discount: float
    actual_amount: float
    status: str
    remark: Optional[str]
    items: List[SaleOrderItemResponse] = []
    created_at: Optional[datetime] = None

    model_config = {"from_attributes": True}
