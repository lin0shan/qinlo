from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime


# ===== Products =====

class ProductCreate(BaseModel):
    name: str = Field(..., max_length=200)
    barcode: Optional[str] = Field(None, max_length=50)
    sku_code: Optional[str] = Field(default="", max_length=20)
    spec: Optional[str] = Field(None, max_length=100)
    brand: Optional[str] = Field(default="", max_length=50)
    category: str = Field(default="其他")
    unit: str = Field(default="个")
    cost_price: float = Field(default=0, ge=0)
    retail_price: float = Field(default=0, ge=0)
    wholesale_price: Optional[float] = Field(default=0, ge=0)
    safety_stock: int = Field(default=10, ge=0)
    remark: Optional[str] = None


class ProductUpdate(BaseModel):
    name: Optional[str] = Field(None, max_length=200)
    barcode: Optional[str] = Field(None, max_length=50)
    sku_code: Optional[str] = Field(None, max_length=20)
    spec: Optional[str] = Field(None, max_length=100)
    brand: Optional[str] = Field(None, max_length=50)
    category: Optional[str] = None
    unit: Optional[str] = None
    cost_price: Optional[float] = Field(None, ge=0)
    retail_price: Optional[float] = Field(None, ge=0)
    wholesale_price: Optional[float] = Field(None, ge=0)
    safety_stock: Optional[int] = Field(None, ge=0)
    remark: Optional[str] = None


class ProductResponse(BaseModel):
    id: int
    name: str
    barcode: Optional[str]
    sku_code: Optional[str] = ""
    spec: Optional[str]
    brand: Optional[str] = ""
    category: str
    unit: str
    image_url: Optional[str]
    cost_price: float
    retail_price: float
    wholesale_price: Optional[float]
    safety_stock: int
    status: str
    remark: Optional[str]
    current_stock: int = 0  # Live inventory stock (filled on query)
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


# ===== Suppliers =====

class SupplierCreate(BaseModel):
    name: str = Field(..., max_length=200)
    contact: Optional[str] = Field(None, max_length=100)
    phone: Optional[str] = Field(None, max_length=30)
    remark: Optional[str] = None


class SupplierResponse(BaseModel):
    id: int
    name: str
    contact: Optional[str]
    phone: Optional[str]
    remark: Optional[str]

    model_config = {"from_attributes": True}
