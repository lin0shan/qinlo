from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas.inventory import InventoryCheckRequest, InventoryInboundRequest
from app.services import order_service

router = APIRouter(prefix="/api/v1", tags=["库存"])


@router.get("/inventory")
def get_inventory(
    keyword: str = Query(None),
    category: str = Query(None),
    brand: str = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
):
    items, total = order_service.get_inventory_list(db, keyword, category, brand, page, page_size)
    return {"items": items, "total": total, "page": page, "page_size": page_size}


@router.get("/inventory/logs")
def get_inventory_logs(
    product_id: int = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
):
    logs, total = order_service.get_inventory_logs(db, product_id, page, page_size)
    # Batch lookup products
    from app.models.product import Product
    pids = list({l.product_id for l in logs})
    products = db.query(Product).filter(Product.id.in_(pids)).all() if pids else []
    product_map = {p.id: p.name for p in products}

    result = []
    for l in logs:
        result.append({
            "id": l.id,
            "product_id": l.product_id,
            "product_name": product_map.get(l.product_id, ""),
            "change_type": l.change_type,
            "change_quantity": l.change_quantity,
            "after_quantity": l.after_quantity,
            "reference_id": l.reference_id,
            "reference_type": l.reference_type,
            "created_at": l.created_at.isoformat() if l.created_at else None,
        })
    return {"items": result, "total": total, "page": page, "page_size": page_size}


@router.post("/inventory/check")
def do_inventory_check(data: InventoryCheckRequest, db: Session = Depends(get_db)):
    results = order_service.do_inventory_check(db, data)
    return {"items": results, "message": "盘点完成"}


@router.post("/inventory/inbound")
def scan_inbound(data: InventoryInboundRequest, db: Session = Depends(get_db)):
    return order_service.do_scan_inbound(db, data.product_id, data.quantity)
