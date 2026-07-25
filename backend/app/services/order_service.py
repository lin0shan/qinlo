from sqlalchemy.orm import Session
from sqlalchemy import func, update
from typing import List, Optional
from datetime import date
from fastapi import HTTPException
from app.models.inventory import InventoryLog
from app.models.product import Product
from app.models.order import PurchaseOrder, PurchaseOrderItem, SaleOrder, SaleOrderItem
from app.models.shipment import Shipment
from app.schemas.order import PurchaseOrderCreate, SaleOrderCreate
from app.schemas.inventory import InventoryCheckRequest
from app.logging import ops_log


# ===== Purchase Orders =====

def create_purchase_order(db: Session, data: PurchaseOrderCreate) -> PurchaseOrder:
    try:
        total = sum(item.unit_price * item.quantity for item in data.items)
        order = PurchaseOrder(supplier_id=data.supplier_id, total_amount=total, remark=data.remark)
        db.add(order)
        db.flush()

        for item_data in data.items:
            db.add(PurchaseOrderItem(
                purchase_order_id=order.id,
                product_id=item_data.product_id,
                quantity=item_data.quantity,
                unit_price=item_data.unit_price,
            ))
            _add_inventory_log(
                db, item_data.product_id, "采购入库", item_data.quantity,
                reference_id=order.id, reference_type="purchase_order"
            )

        db.commit()
        db.refresh(order)
        ops_log.info("purchase_order_created", order_id=order.id, total_amount=total)
        return order
    except Exception:
        db.rollback()
        raise


def list_purchase_orders(db: Session, page: int = 1, page_size: int = 20):
    q = db.query(PurchaseOrder)
    total = q.count()
    items = q.order_by(PurchaseOrder.created_at.desc()).offset((page - 1) * page_size).limit(page_size).all()
    return items, total


def get_purchase_order(db: Session, order_id: int) -> Optional[PurchaseOrder]:
    return db.query(PurchaseOrder).filter(PurchaseOrder.id == order_id).first()


# ===== Sale Orders =====

def create_sale_order(db: Session, data: SaleOrderCreate) -> SaleOrder:
    try:
        # Stock validation: all products must have sufficient stock
        product_ids = [item.product_id for item in data.items]
        stock_map = _get_stock_map(db, product_ids)
        for item in data.items:
            stock = stock_map.get(item.product_id, 0)
            if stock < item.quantity:
                raise HTTPException(status_code=400, detail=f"库存不足：商品ID {item.product_id} 当前库存 {stock}，需要 {item.quantity}")

        total = sum(item.unit_price * item.quantity for item in data.items)
        actual = total - data.discount

        today_str = date.today().strftime("%Y%m%d")
        latest = (
            db.query(SaleOrder)
            .filter(SaleOrder.order_number.like(f"{today_str}%"))
            .order_by(SaleOrder.order_number.desc())
            .first()
        )
        seq = int(latest.order_number[8:]) + 1 if latest and latest.order_number else 1
        order_number = f"{today_str}{seq:03d}"

        order = SaleOrder(
            order_number=order_number, member_id=data.member_id,
            total_amount=total, discount=data.discount, actual_amount=actual, remark=data.remark,
        )
        db.add(order)
        db.flush()

        for item_data in data.items:
            db.add(SaleOrderItem(
                sale_order_id=order.id,
                product_id=item_data.product_id,
                quantity=item_data.quantity,
                unit_price=item_data.unit_price,
            ))
            _add_inventory_log(
                db, item_data.product_id, "销售出库", -item_data.quantity,
                reference_id=order.id, reference_type="sale_order"
            )

        if data.member_id:
            from app.models.member import Member
            member = db.query(Member).filter(Member.id == data.member_id).first()
            if member:
                member.total_spent = (member.total_spent or 0) + actual
                member.points = (member.points or 0) + int(actual)

        # Auto-create pending shipment record
        shipment = Shipment(sale_order_id=order.id, ship_status="未发货")
        db.add(shipment)

        db.commit()
        db.refresh(order)
        ops_log.info("sale_order_created", order_id=order.id, total_amount=total, actual_amount=actual, order_number=order_number)
        return order
    except Exception:
        db.rollback()
        raise


def list_sale_orders(db: Session, page: int = 1, page_size: int = 20, month: Optional[str] = None):
    q = db.query(SaleOrder)
    if month:
        q = q.filter(func.strftime("%Y%m", SaleOrder.created_at) == month)
    total = q.count()
    items = q.order_by(SaleOrder.created_at.desc()).offset((page - 1) * page_size).limit(page_size).all()
    return items, total


def get_sale_order(db: Session, order_id: int) -> Optional[SaleOrder]:
    return db.query(SaleOrder).filter(SaleOrder.id == order_id).first()


# ===== Returns =====

def return_purchase_order(db: Session, order_id: int) -> Optional[PurchaseOrder]:
    try:
        order = get_purchase_order(db, order_id)
        if not order:
            return None
        for item in order.items:
            _add_inventory_log(
                db, item.product_id, "采购退货入库", -item.quantity,
                reference_id=order.id, reference_type="purchase_return"
            )
        order.status = "已退货"
        db.commit()
        ops_log.info("purchase_returned", order_id=order_id)
        return order
    except Exception:
        db.rollback()
        raise


def return_sale_order(db: Session, order_id: int) -> Optional[SaleOrder]:
    try:
        order = get_sale_order(db, order_id)
        if not order:
            return None
        for item in order.items:
            _add_inventory_log(
                db, item.product_id, "销售退货入库", item.quantity,
                reference_id=order.id, reference_type="sale_return"
            )
        order.status = "已退货"
        # Deduct member spending and points
        if order.member_id:
            from app.models.member import Member, MemberPoints
            member = db.query(Member).filter(Member.id == order.member_id).first()
            if member:
                actual = order.actual_amount or 0
                member.total_spent = max(0, (member.total_spent or 0) - actual)
                member.points = max(0, (member.points or 0) - int(actual))
                mp = db.query(MemberPoints).filter(
                    MemberPoints.member_id == order.member_id,
                    MemberPoints.brand == "赫莲娜",
                ).first()
                if mp:
                    mp.points = max(0, mp.points - int(actual))
        db.commit()
        ops_log.info("sale_returned", order_id=order_id)
        return order
    except Exception:
        db.rollback()
        raise


# ===== Inventory =====

def get_inventory_list(db: Session, keyword: Optional[str] = None, category: Optional[str] = None, brand: Optional[str] = None, page: int = 1, page_size: int = 20):
    q = db.query(Product)
    if keyword:
        q = q.filter(
            Product.name.ilike(f"%{keyword}%") | Product.barcode.ilike(f"%{keyword}%") | Product.sku_code.ilike(f"%{keyword}%") | Product.brand.ilike(f"%{keyword}%")
        )
    if category:
        q = q.filter(Product.category == category)
    if brand:
        q = q.filter(Product.brand == brand)
    total = q.count()
    products = q.order_by(Product.name).offset((page - 1) * page_size).limit(page_size).all()

    product_ids = [p.id for p in products]
    stock_map = _get_stock_map(db, product_ids)

    result = []
    for p in products:
        stock = stock_map.get(p.id, 0)
        if stock <= 0:
            status = "shortage"
        elif stock <= p.safety_stock:
            status = "warning"
        else:
            status = "normal"
        result.append({
            "product_id": p.id,
            "product_name": p.name,
            "barcode": p.barcode,
            "sku_code": p.sku_code or "",
            "spec": p.spec,
            "brand": p.brand or "",
            "category": p.category,
            "unit": p.unit,
            "image_url": p.image_url,
            "retail_price": p.retail_price,
            "safety_stock": p.safety_stock,
            "current_stock": stock,
            "status": status,
        })
    return result, total


def get_inventory_logs(db: Session, product_id: Optional[int] = None, page: int = 1, page_size: int = 50):
    q = db.query(InventoryLog)
    if product_id:
        q = q.filter(InventoryLog.product_id == product_id)
    total = q.count()
    logs = q.order_by(InventoryLog.created_at.desc()).offset((page - 1) * page_size).limit(page_size).all()
    return logs, total


def do_inventory_check(db: Session, data: InventoryCheckRequest):
    """盘点：对比系统库存与实际库存，差异生成调整记录"""
    try:
        results = []
        for item in data.items:
            stock = _get_single_stock(db, item.product_id)
            diff = item.actual_quantity - stock
            if diff != 0:
                _add_inventory_log(
                    db, item.product_id, "盘点调整", diff,
                    reference_id=0, reference_type="inventory_check"
                )
            product = db.query(Product).filter(Product.id == item.product_id).first()
            results.append({
                "product_id": item.product_id,
                "product_name": product.name if product else "",
                "system_quantity": stock,
                "actual_quantity": item.actual_quantity,
                "difference": diff,
            })
        db.commit()
        ops_log.info("inventory_check_done", items_count=len(data.items))
        return results
    except Exception:
        db.rollback()
        raise


# ===== Internal Utilities =====

def _add_inventory_log(db: Session, product_id: int, change_type: str, quantity: int,
                       reference_id: int = 0, reference_type: str = ""):
    after = _get_single_stock(db, product_id) + quantity
    log = InventoryLog(
        product_id=product_id,
        change_type=change_type,
        change_quantity=quantity,
        after_quantity=after,
        reference_id=reference_id,
        reference_type=reference_type,
    )
    db.add(log)
    # Sync Product.current_stock denormalized field
    db.execute(update(Product).where(Product.id == product_id).values(current_stock=after))
    db.flush()


def _get_stock_map(db: Session, product_ids: list[int]) -> dict[int, int]:
    if not product_ids:
        return {}
    rows = (
        db.query(Product.id, Product.current_stock)
        .filter(Product.id.in_(product_ids))
        .all()
    )
    return {row[0]: (row[1] or 0) for row in rows}


def _get_single_stock(db: Session, product_id: int) -> int:
    result = db.query(Product.current_stock).filter(Product.id == product_id).scalar()
    return result or 0


def do_scan_inbound(db: Session, product_id: int, quantity: int) -> dict:
    """扫码直接入库，不关联供应商/采购单"""
    try:
        product = db.query(Product).filter(Product.id == product_id).first()
        if not product:
            raise ValueError("商品不存在")
        _add_inventory_log(
            db, product_id, "扫码入库", quantity,
            reference_id=0, reference_type="scan_inbound"
        )
        db.commit()
        new_stock = _get_single_stock(db, product_id)
        ops_log.info("scan_inbound", product_id=product_id, quantity=quantity, new_stock=new_stock)
        return {
            "product_id": product_id,
            "product_name": product.name,
            "quantity": quantity,
            "current_stock": new_stock,
            "message": f"{product.name} 入库 {quantity} 件",
        }
    except Exception:
        db.rollback()
        raise
