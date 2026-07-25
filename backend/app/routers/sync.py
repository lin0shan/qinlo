from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field
from typing import List, Optional, Any
from datetime import datetime
import hashlib

from app.database import get_db
from app.models.product import Product
from app.models.member import Member
from app.models.inventory import InventoryLog
from app.models.order import SaleOrder, SaleOrderItem
from app.services.order_service import create_sale_order
from app.schemas.order import SaleOrderCreate, SaleOrderItemCreate
from app.logging import ops_log

router = APIRouter(prefix="/api/v1/sync", tags=["Offline Sync"])


class SyncOperation(BaseModel):
    action: str = Field(..., description="Operation type: sale_order_create, member_create")
    payload: dict
    client_id: Optional[str] = None
    timestamp: Optional[str] = None


class SyncBatchRequest(BaseModel):
    operations: List[SyncOperation]
    client_id: Optional[str] = None


class SyncResultItem(BaseModel):
    client_id: Optional[str] = None
    action: str
    success: bool
    server_id: Optional[int] = None
    message: Optional[str] = None


@router.post("/batch")
def sync_batch(request: SyncBatchRequest, db: Session = Depends(get_db)):
    """批量处理离线操作队列"""
    results: list[dict] = []

    for op in request.operations:
        try:
            result = _process_operation(db, op)
            results.append(result)
        except Exception as e:
            results.append({
                "client_id": op.client_id,
                "action": op.action,
                "success": False,
                "message": str(e),
            })

    db.commit()

    success_count = sum(1 for r in results if r["success"])
    fail_count = len(results) - success_count
    ops_log.info("sync_batch_processed", total=len(results), success=success_count, fail=fail_count)

    return {
        "results": results,
        "summary": {"total": len(results), "success": success_count, "fail": fail_count},
    }


def _process_operation(db: Session, op: SyncOperation) -> dict:
    payload = op.payload

    if op.action == "sale_order_create":
        items_data = payload.get("items", [])
        items = [SaleOrderItemCreate(**i) for i in items_data]
        data = SaleOrderCreate(
            member_id=payload.get("member_id"),
            items=items,
            discount=payload.get("discount", 0),
            remark=f"[离线同步] {payload.get('remark', '')}",
        )
        order = create_sale_order(db, data)
        return {"client_id": op.client_id, "action": op.action, "success": True, "server_id": order.id}

    elif op.action == "member_create":
        existing = db.query(Member).filter(Member.phone == payload.get("phone")).first()
        if existing:
            raise ValueError(f"手机号 {payload['phone']} 已存在")
        member = Member(
            name=payload.get("name", ""),
            phone=payload.get("phone", ""),
            gender=payload.get("gender"),
            birthday=payload.get("birthday"),
            skin_type=payload.get("skin_type"),
            tags=payload.get("tags"),
        )
        db.add(member)
        db.flush()
        return {"client_id": op.client_id, "action": op.action, "success": True, "server_id": member.id}

    return {"client_id": op.client_id, "action": op.action, "success": False, "message": f"未知操作: {op.action}"}


@router.get("/version")
def sync_version(db: Session = Depends(get_db)):
    """获取当前数据版本号，用于增量同步判断"""
    max_updated = db.query(Product.updated_at).order_by(Product.updated_at.desc()).first()
    version_str = max_updated[0].isoformat() if max_updated and max_updated[0] else "2024-01-01T00:00:00"

    member_count = db.query(Member).count()
    product_count = db.query(Product).count()
    order_count = db.query(SaleOrder).count()
    log_count = db.query(InventoryLog).count()

    version_hash = hashlib.md5(
        f"{version_str}-m{member_count}-p{product_count}-o{order_count}-l{log_count}".encode()
    ).hexdigest()[:12]

    return {
        "version": version_hash,
        "updated_at": version_str,
        "stats": {
            "members": member_count,
            "products": product_count,
            "orders": order_count,
            "inventory_logs": log_count,
        },
    }
