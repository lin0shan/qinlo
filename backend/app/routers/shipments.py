from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from app.database import get_db
from app.schemas.shipment import ShipmentCreate, ShipmentUpdate
from app.services import shipment_service
from app.models.order import SaleOrder

router = APIRouter(prefix="/api/v1", tags=["发货"])


@router.post("/sale-orders/{order_id}/shipments", status_code=201)
def create_shipment(order_id: int, data: ShipmentCreate, db: Session = Depends(get_db)):
    shipment = shipment_service.create_shipment(db, order_id, data)
    return {
        "id": shipment.id,
        "sale_order_id": shipment.sale_order_id,
        "express_company": shipment.express_company,
        "express_no": shipment.express_no,
        "ship_status": shipment.ship_status,
        "message": "发货单创建成功",
    }


@router.get("/shipments")
def list_shipments(
    sale_order_id: int = Query(None),
    ship_status: str = Query(None, description="按发货状态筛选"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
):
    items, total = shipment_service.list_shipments(db, sale_order_id, ship_status, page, page_size)
    # Preload order_number mapping
    order_ids = list(set(s.sale_order_id for s in items))
    order_map = {}
    if order_ids:
        orders = db.query(SaleOrder).filter(SaleOrder.id.in_(order_ids)).all()
        order_map = {o.id: o for o in orders}

    result = [
        {
            "id": s.id, "sale_order_id": s.sale_order_id,
            "order_number": order_map[s.sale_order_id].order_number if s.sale_order_id in order_map else None,
            "express_company": s.express_company, "express_no": s.express_no,
            "ship_status": s.ship_status,
            "receiver_name": s.receiver_name, "receiver_phone": s.receiver_phone,
            "receiver_address": s.receiver_address, "remark": s.remark,
            "created_at": s.created_at.isoformat() if s.created_at else None,
        }
        for s in items
    ]
    return {"items": result, "total": total, "page": page, "page_size": page_size}


@router.patch("/shipments/{shipment_id}")
def update_shipment(shipment_id: int, data: ShipmentUpdate, db: Session = Depends(get_db)):
    shipment = shipment_service.update_shipment(db, shipment_id, data)
    if not shipment:
        raise HTTPException(404, detail="发货单不存在")
    return {"message": "发货信息已更新", "ship_status": shipment.ship_status}
