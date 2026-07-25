from typing import Optional
from sqlalchemy.orm import Session
from app.models.shipment import Shipment
from app.models.order import SaleOrder
from app.schemas.shipment import ShipmentCreate, ShipmentUpdate
from app.logging import ops_log


def create_shipment(db: Session, sale_order_id: int, data: ShipmentCreate) -> Shipment:
    shipment = Shipment(sale_order_id=sale_order_id, **data.model_dump())
    db.add(shipment)
    db.commit()
    db.refresh(shipment)
    ops_log.info("shipment_created", shipment_id=shipment.id, sale_order_id=sale_order_id)
    return shipment


def list_shipments(db: Session, sale_order_id: Optional[int] = None, ship_status: Optional[str] = None, page: int = 1, page_size: int = 20):
    q = db.query(Shipment)
    if sale_order_id:
        q = q.filter(Shipment.sale_order_id == sale_order_id)
    if ship_status:
        q = q.filter(Shipment.ship_status == ship_status)
    total = q.count()
    items = q.order_by(Shipment.created_at.desc()).offset((page - 1) * page_size).limit(page_size).all()
    return items, total


def get_shipment(db: Session, shipment_id: int) -> Optional[Shipment]:
    return db.query(Shipment).filter(Shipment.id == shipment_id).first()


def update_shipment(db: Session, shipment_id: int, data: ShipmentUpdate) -> Optional[Shipment]:
    shipment = get_shipment(db, shipment_id)
    if not shipment:
        return None
    update_data = data.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(shipment, key, value)
    db.commit()
    db.refresh(shipment)
    ops_log.info("shipment_updated", shipment_id=shipment_id)
    return shipment
