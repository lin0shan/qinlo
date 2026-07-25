from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile, File
from sqlalchemy.orm import Session
from fastapi.responses import StreamingResponse
from io import BytesIO

from app.database import get_db
from app.schemas.product import ProductCreate, ProductUpdate, ProductResponse, SupplierCreate, SupplierResponse
from app.services import product_service
from app.models.supplier import Supplier
from app.utils.image import compress_image
from app.utils.barcode_util import generate_barcode_image

router = APIRouter(prefix="/api/v1", tags=["商品 & 供应商"])


# ==================== Products ====================

@router.get("/brands")
def list_brands(db: Session = Depends(get_db)):
    """列出所有品牌（去重排序）"""
    from app.models.product import Product
    from sqlalchemy import distinct
    rows = db.query(distinct(Product.brand)).filter(Product.brand != "", Product.brand.isnot(None)).order_by(Product.brand).all()
    return [r[0] for r in rows]


@router.get("/products", response_model=dict)
def list_products(
    keyword: str = Query(None, description="Search keyword (name/barcode/brand)"),
    category: str = Query(None, description="Category filter"),
    brand: str = Query(None, description="Brand filter"),
    status: str = Query(None, description="Status filter"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
):
    items, total, stock_map = product_service.list_products(db, keyword, category, brand, status, page, page_size)
    result = []
    for p in items:
        d = {
            "id": p.id, "name": p.name, "barcode": p.barcode, "sku_code": p.sku_code or "", "spec": p.spec,
            "brand": p.brand or "", "category": p.category, "unit": p.unit, "image_url": p.image_url,
            "cost_price": p.cost_price, "retail_price": p.retail_price,
            "wholesale_price": p.wholesale_price, "safety_stock": p.safety_stock,
            "status": p.status, "remark": p.remark,
            "current_stock": stock_map.get(p.id, 0),
            "created_at": p.created_at.isoformat() if p.created_at else None,
            "updated_at": p.updated_at.isoformat() if p.updated_at else None,
        }
        result.append(d)
    return {"items": result, "total": total, "page": page, "page_size": page_size}


@router.post("/products", status_code=201)
def create_product(data: ProductCreate, db: Session = Depends(get_db)):
    if data.barcode and product_service.check_barcode_exists(db, data.barcode):
        raise HTTPException(409, detail="条码已存在")
    product = product_service.create_product(db, data)
    return {"id": product.id, "message": "商品创建成功"}


@router.put("/products/{product_id}")
def update_product(product_id: int, data: ProductUpdate, db: Session = Depends(get_db)):
    if data.barcode and product_service.check_barcode_exists(db, data.barcode, exclude_id=product_id):
        raise HTTPException(409, detail="条码已存在")
    product = product_service.update_product(db, product_id, data)
    if not product:
        raise HTTPException(404, detail="商品不存在")
    return {"message": "更新成功"}


@router.patch("/products/{product_id}/status")
def set_product_status(
    product_id: int,
    status: str = Query(..., pattern="^(在售|停售)$"),
    db: Session = Depends(get_db),
):
    product = product_service.set_product_status(db, product_id, status)
    if not product:
        raise HTTPException(404, detail="商品不存在")
    return {"message": f"商品已{status}"}


@router.post("/products/{product_id}/image")
def upload_product_image(
    product_id: int,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    product = product_service.get_product(db, product_id)
    if not product:
        raise HTTPException(404, detail="商品不存在")

    content = file.file.read()
    url = compress_image(content, product_id, file.filename or "image.jpg")
    product.image_url = url
    db.commit()
    return {"image_url": url, "message": "图片上传成功"}


@router.post("/products/{product_id}/barcode")
def generate_barcode(product_id: int, prefix: str = Query("BH", max_length=4), db: Session = Depends(get_db)):
    product = product_service.get_product(db, product_id)
    if not product:
        raise HTTPException(404, detail="商品不存在")

    # Return existing barcode directly to avoid unique constraint violations
    if product.barcode:
        barcode_str = product.barcode
        _, img_bytes = generate_barcode_image(prefix, product_id)
    else:
        barcode_str, img_bytes = generate_barcode_image(prefix, product_id)
        product.barcode = barcode_str
        db.commit()

    return StreamingResponse(
        BytesIO(img_bytes),
        media_type="image/png",
        headers={"X-Barcode-String": barcode_str},
    )


# ==================== Suppliers ====================

@router.get("/suppliers")
def list_suppliers(db: Session = Depends(get_db)):
    suppliers = db.query(Supplier).order_by(Supplier.name).all()
    return [
        {"id": s.id, "name": s.name, "contact": s.contact, "phone": s.phone, "remark": s.remark}
        for s in suppliers
    ]


@router.post("/suppliers", status_code=201)
def create_supplier(data: SupplierCreate, db: Session = Depends(get_db)):
    supplier = Supplier(**data.model_dump())
    db.add(supplier)
    db.commit()
    db.refresh(supplier)
    return {"id": supplier.id, "message": "供应商创建成功"}
