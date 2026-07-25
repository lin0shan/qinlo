from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime


class InventoryResponse(BaseModel):
    product_id: int
    product_name: str
    barcode: Optional[str]
    spec: Optional[str]
    category: str
    unit: str
    image_url: Optional[str]
    retail_price: float
    safety_stock: int
    current_stock: int
    status: str  # normal / warning / shortage


class InventoryLogResponse(BaseModel):
    id: int
    product_id: int
    product_name: str = ""
    change_type: str
    change_quantity: int
    after_quantity: int
    reference_id: Optional[int]
    reference_type: Optional[str]
    created_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


class InventoryCheckItem(BaseModel):
    product_id: int
    actual_quantity: int = Field(..., ge=0)


class InventoryCheckRequest(BaseModel):
    items: List[InventoryCheckItem] = Field(..., min_length=1)
    remark: Optional[str] = None


class InventoryCheckResponse(BaseModel):
    product_id: int
    product_name: str
    system_quantity: int
    actual_quantity: int
    difference: int


class InventoryInboundRequest(BaseModel):
    product_id: int
    quantity: int = Field(..., gt=0, le=9999)
