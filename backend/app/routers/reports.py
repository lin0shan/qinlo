"""Reports API: daily/monthly sales, daily/monthly purchases, top-selling products."""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import func, extract
from datetime import date, timedelta

from app.database import get_db
from app.models.order import SaleOrder, SaleOrderItem
from app.models.product import Product
from app.models.member import Member
from app.models.inventory import InventoryLog

router = APIRouter(prefix="/api/v1", tags=["报表"])


@router.get("/reports/sales")
def sales_report(
    period: str = Query("daily", pattern="^(daily|monthly)$"),
    start_date: str = Query(None, description="YYYY-MM-DD, default today"),
    end_date: str = Query(None, description="YYYY-MM-DD, default today"),
    db: Session = Depends(get_db),
):
    """Sales report: daily/monthly, defaults to last 30 days."""
    today = date.today()
    if start_date:
        sd = date.fromisoformat(start_date)
    else:
        sd = today - timedelta(days=30)

    if end_date:
        ed = date.fromisoformat(end_date)
    else:
        ed = today

    # Query sale orders (normal status, exclude returns)
    q = db.query(SaleOrder).filter(
        SaleOrder.status != "已退货",
        func.date(SaleOrder.created_at) >= sd,
        func.date(SaleOrder.created_at) <= ed,
    )

    if period == "daily":
        # Group by day
        rows = (
            q.with_entities(
                func.date(SaleOrder.created_at).label("date"),
                func.count(SaleOrder.id).label("order_count"),
                func.sum(SaleOrder.total_amount).label("total_amount"),
                func.sum(SaleOrder.discount).label("total_discount"),
                func.sum(SaleOrder.actual_amount).label("actual_amount"),
            )
            .group_by(func.date(SaleOrder.created_at))
            .order_by(func.date(SaleOrder.created_at).desc())
            .all()
        )
        result = [
            {
                "date": str(r.date),
                "order_count": r.order_count,
                "total_amount": round(r.total_amount or 0, 2),
                "total_discount": round(r.total_discount or 0, 2),
                "actual_amount": round(r.actual_amount or 0, 2),
                "gross_profit": round((r.actual_amount or 0) - _get_cost(db, sd, ed), 2),
            }
            for r in rows
        ]
    else:
        # Group by month
        rows = (
            q.with_entities(
                extract("year", SaleOrder.created_at).label("year"),
                extract("month", SaleOrder.created_at).label("month"),
                func.count(SaleOrder.id).label("order_count"),
                func.sum(SaleOrder.total_amount).label("total_amount"),
                func.sum(SaleOrder.discount).label("total_discount"),
                func.sum(SaleOrder.actual_amount).label("actual_amount"),
            )
            .group_by(
                extract("year", SaleOrder.created_at),
                extract("month", SaleOrder.created_at),
            )
            .order_by(
                extract("year", SaleOrder.created_at).desc(),
                extract("month", SaleOrder.created_at).desc(),
            )
            .all()
        )
        result = [
            {
                "year": int(r.year),
                "month": int(r.month),
                "order_count": r.order_count,
                "total_amount": round(r.total_amount or 0, 2),
                "total_discount": round(r.total_discount or 0, 2),
                "actual_amount": round(r.actual_amount or 0, 2),
            }
            for r in rows
        ]

    # Summary
    summary = {
        "total_orders": sum(r["order_count"] for r in result),
        "total_amount": round(sum(r["total_amount"] for r in result), 2),
        "total_actual": round(sum(r["actual_amount"] for r in result), 2),
    }

    return {"items": result, "summary": summary, "period": period}


@router.get("/reports/top-products")
def top_products(
    limit: int = Query(10, ge=1, le=50),
    sort_by: str = Query("quantity", pattern="^(quantity|amount)$"),
    db: Session = Depends(get_db),
):
    """热销商品排行"""
    if sort_by == "quantity":
        rows = (
            db.query(
                SaleOrderItem.product_id,
                func.sum(SaleOrderItem.quantity).label("total_quantity"),
                func.sum(SaleOrderItem.quantity * SaleOrderItem.unit_price).label("total_amount"),
            )
            .join(SaleOrder, SaleOrderItem.sale_order_id == SaleOrder.id)
            .filter(SaleOrder.status != "已退货")
            .group_by(SaleOrderItem.product_id)
            .order_by(func.sum(SaleOrderItem.quantity).desc())
            .limit(limit)
            .all()
        )
    else:
        rows = (
            db.query(
                SaleOrderItem.product_id,
                func.sum(SaleOrderItem.quantity).label("total_quantity"),
                func.sum(SaleOrderItem.quantity * SaleOrderItem.unit_price).label("total_amount"),
            )
            .join(SaleOrder, SaleOrderItem.sale_order_id == SaleOrder.id)
            .filter(SaleOrder.status != "已退货")
            .group_by(SaleOrderItem.product_id)
            .order_by(func.sum(SaleOrderItem.quantity * SaleOrderItem.unit_price).desc())
            .limit(limit)
            .all()
        )

    product_ids = [r.product_id for r in rows]
    products_map = {
        p.id: p for p in db.query(Product).filter(Product.id.in_(product_ids)).all()
    }

    return {
        "items": [
            {
                "product_id": r.product_id,
                "product_name": products_map.get(r.product_id, Product()).name,
                "total_quantity": r.total_quantity,
                "total_amount": round(r.total_amount or 0, 2),
            }
            for r in rows
        ]
    }


@router.get("/reports/inbound")
def inbound_report(
    period: str = Query("daily", pattern="^(daily|monthly)$"),
    start_date: str = Query(None, description="YYYY-MM-DD"),
    end_date: str = Query(None, description="YYYY-MM-DD"),
    db: Session = Depends(get_db),
):
    """Purchase report: daily/monthly (purchase + scan), defaults to last 30 days."""
    today = date.today()
    if start_date:
        sd = date.fromisoformat(start_date)
    else:
        sd = today - timedelta(days=30)

    if end_date:
        ed = date.fromisoformat(end_date)
    else:
        ed = today

    q = db.query(InventoryLog).filter(
        InventoryLog.change_type.in_(["采购入库", "扫码入库", "其它入库"]),
        func.date(InventoryLog.created_at) >= sd,
        func.date(InventoryLog.created_at) <= ed,
    )

    if period == "daily":
        rows = (
            q.with_entities(
                func.date(InventoryLog.created_at).label("date"),
                func.count(InventoryLog.id).label("inbound_count"),
                func.sum(InventoryLog.change_quantity).label("total_quantity"),
            )
            .group_by(func.date(InventoryLog.created_at))
            .order_by(func.date(InventoryLog.created_at).desc())
            .all()
        )
        result = [
            {
                "date": str(r.date),
                "inbound_count": r.inbound_count,
                "total_quantity": r.total_quantity or 0,
            }
            for r in rows
        ]
    else:
        rows = (
            q.with_entities(
                extract("year", InventoryLog.created_at).label("year"),
                extract("month", InventoryLog.created_at).label("month"),
                func.count(InventoryLog.id).label("inbound_count"),
                func.sum(InventoryLog.change_quantity).label("total_quantity"),
            )
            .group_by(
                extract("year", InventoryLog.created_at),
                extract("month", InventoryLog.created_at),
            )
            .order_by(
                extract("year", InventoryLog.created_at).desc(),
                extract("month", InventoryLog.created_at).desc(),
            )
            .all()
        )
        result = [
            {
                "year": int(r.year),
                "month": int(r.month),
                "inbound_count": r.inbound_count,
                "total_quantity": r.total_quantity or 0,
            }
            for r in rows
        ]

    summary = {
        "total_inbounds": sum(r["inbound_count"] for r in result),
        "total_quantity": sum(r["total_quantity"] for r in result),
    }

    return {"items": result, "summary": summary, "period": period}


@router.get("/reports/inventory-top")
def inventory_top(
    limit: int = Query(10, ge=1, le=50),
    db: Session = Depends(get_db),
):
    """库存量排行：当前库存从大到小"""
    rows = (
        db.query(
            InventoryLog.product_id,
            func.sum(InventoryLog.change_quantity).label("current_stock"),
        )
        .group_by(InventoryLog.product_id)
        .order_by(func.sum(InventoryLog.change_quantity).desc())
        .limit(limit)
        .all()
    )

    product_ids = [r.product_id for r in rows]
    products_map = {
        p.id: p for p in db.query(Product).filter(Product.id.in_(product_ids)).all()
    }

    return {
        "items": [
            {
                "product_id": r.product_id,
                "product_name": products_map.get(r.product_id, Product()).name,
                "current_stock": r.current_stock or 0,
            }
            for r in rows
        ]
    }


def _get_cost(db: Session, start: date, end: date) -> float:
    """估算时间段内的成本总额"""
    items = (
        db.query(
            func.sum(SaleOrderItem.quantity * Product.cost_price)
        )
        .join(SaleOrder, SaleOrderItem.sale_order_id == SaleOrder.id)
        .join(Product, SaleOrderItem.product_id == Product.id)
        .filter(
            SaleOrder.status != "已退货",
            func.date(SaleOrder.created_at) >= start,
            func.date(SaleOrder.created_at) <= end,
        )
        .scalar()
    )
    return items or 0
