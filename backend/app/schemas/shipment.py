from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime


class ShipmentCreate(BaseModel):
    express_company: Optional[str] = Field(None, max_length=50)
    express_no: Optional[str] = Field(None, max_length=100)
    receiver_name: Optional[str] = Field(None, max_length=100)
    receiver_phone: Optional[str] = Field(None, max_length=30)
    receiver_address: Optional[str] = None
    remark: Optional[str] = None


class ShipmentUpdate(BaseModel):
    express_company: Optional[str] = Field(None, max_length=50)
    express_no: Optional[str] = Field(None, max_length=100)
    ship_status: Optional[str] = None
    receiver_name: Optional[str] = Field(None, max_length=100)
    receiver_phone: Optional[str] = Field(None, max_length=30)
    receiver_address: Optional[str] = None
    remark: Optional[str] = None


class ShipmentResponse(BaseModel):
    id: int
    sale_order_id: int
    express_company: Optional[str]
    express_no: Optional[str]
    ship_status: str
    receiver_name: Optional[str]
    receiver_phone: Optional[str]
    receiver_address: Optional[str]
    remark: Optional[str]
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    model_config = {"from_attributes": True}
