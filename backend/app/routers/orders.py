from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas.order import PurchaseOrderCreate, SaleOrderCreate
from app.services import order_service

router = APIRouter(prefix="/api/v1", tags=["采购 & 销售"])


# ==================== Purchase Orders ====================

@router.post("/purchase-orders", status_code=201)
def create_purchase_order(data: PurchaseOrderCreate, db: Session = Depends(get_db)):
    order = order_service.create_purchase_order(db, data)
    return {"id": order.id, "total_amount": order.total_amount, "message": "采购入库完成"}


@router.get("/purchase-orders")
def list_purchase_orders(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
):
    items, total = order_service.list_purchase_orders(db, page, page_size)
    result = []
    for o in items:
        result.append({
            "id": o.id,
            "supplier_id": o.supplier_id,
            "supplier_name": o.supplier.name if o.supplier else "",
            "total_amount": o.total_amount,
            "status": o.status,
            "remark": o.remark,
            "items": [
                {"id": i.id, "product_id": i.product_id, "product_name": i.product.name if i.product else "",
                 "quantity": i.quantity, "unit_price": i.unit_price}
                for i in o.items
            ],
            "created_at": o.created_at.isoformat() if o.created_at else None,
        })
    return {"items": result, "total": total, "page": page, "page_size": page_size}


@router.get("/purchase-orders/{order_id}")
def get_purchase_order(order_id: int, db: Session = Depends(get_db)):
    o = order_service.get_purchase_order(db, order_id)
    if not o:
        raise HTTPException(404, detail="采购单不存在")
    return {
        "id": o.id,
        "supplier_id": o.supplier_id,
        "supplier_name": o.supplier.name if o.supplier else "",
        "total_amount": o.total_amount,
        "status": o.status,
        "remark": o.remark,
        "items": [
            {"id": i.id, "product_id": i.product_id, "product_name": i.product.name if i.product else "",
             "quantity": i.quantity, "unit_price": i.unit_price}
            for i in o.items
        ],
        "created_at": o.created_at.isoformat() if o.created_at else None,
    }


# ==================== Sale Orders ====================

@router.post("/sale-orders", status_code=201)
def create_sale_order(data: SaleOrderCreate, db: Session = Depends(get_db)):
    order = order_service.create_sale_order(db, data)
    return {"id": order.id, "order_number": order.order_number, "actual_amount": order.actual_amount, "message": "销售完成"}


@router.get("/sale-orders")
def list_sale_orders(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    month: str = Query(None, description="Filter by month, format YYYYMM"),
    db: Session = Depends(get_db),
):
    items, total = order_service.list_sale_orders(db, page, page_size, month)
    result = []
    for o in items:
        result.append({
            "id": o.id,
            "order_number": o.order_number,
            "member_id": o.member_id,
            "member_name": o.member.name if o.member else None,
            "total_amount": o.total_amount,
            "discount": o.discount,
            "actual_amount": o.actual_amount,
            "status": o.status,
            "remark": o.remark,
            "items": [
                {"id": i.id, "product_id": i.product_id, "product_name": i.product.name if i.product else "",
                 "quantity": i.quantity, "unit_price": i.unit_price}
                for i in o.items
            ],
            "created_at": o.created_at.isoformat() if o.created_at else None,
        })
    return {"items": result, "total": total, "page": page, "page_size": page_size}


@router.get("/sale-orders/{order_id}")
def get_sale_order(order_id: int, db: Session = Depends(get_db)):
    o = order_service.get_sale_order(db, order_id)
    if not o:
        raise HTTPException(404, detail="销售单不存在")
    return {
        "id": o.id,
        "order_number": o.order_number,
        "member_id": o.member_id,
        "member_name": o.member.name if o.member else None,
        "total_amount": o.total_amount,
        "discount": o.discount,
        "actual_amount": o.actual_amount,
        "status": o.status,
        "remark": o.remark,
        "items": [
            {"id": i.id, "product_id": i.product_id, "product_name": i.product.name if i.product else "",
             "quantity": i.quantity, "unit_price": i.unit_price}
            for i in o.items
        ],
        "created_at": o.created_at.isoformat() if o.created_at else None,
    }


# ==================== Returns ====================

@router.post("/purchase-orders/{order_id}/return")
def return_purchase(order_id: int, db: Session = Depends(get_db)):
    order = order_service.return_purchase_order(db, order_id)
    if not order:
        raise HTTPException(404, detail="采购单不存在")
    return {"message": "采购退货完成，库存已扣减"}


@router.post("/sale-orders/{order_id}/return")
def return_sale(order_id: int, db: Session = Depends(get_db)):
    order = order_service.return_sale_order(db, order_id)
    if not order:
        raise HTTPException(404, detail="销售单不存在")
    return {"message": "销售退货完成，库存已恢复"}
