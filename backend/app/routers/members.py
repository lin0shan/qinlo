from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from app.database import get_db
from app.schemas.member import (
    MemberCreate, MemberUpdate, PointAdjust,
    BatchPointsRequest, BatchCouponRequest,
)
from app.services import member_service

router = APIRouter(prefix="/api/v1", tags=["会员"])


@router.get("/members")
def list_members(
    keyword: str = Query(None),
    tags: str = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
):
    items, total = member_service.list_members(db, keyword, tags, page, page_size)
    return {"items": items, "total": total, "page": page, "page_size": page_size}


@router.post("/members", status_code=201)
def create_member(data: MemberCreate, db: Session = Depends(get_db)):
    try:
        member = member_service.create_member(db, data)
        return {"id": member.id, "message": "会员创建成功"}
    except ValueError as e:
        raise HTTPException(409, detail=str(e))


@router.put("/members/{member_id}")
def update_member(member_id: int, data: MemberUpdate, db: Session = Depends(get_db)):
    try:
        member = member_service.update_member(db, member_id, data)
        if not member:
            raise HTTPException(404, detail="会员不存在")
        return {"message": "更新成功"}
    except ValueError as e:
        raise HTTPException(409, detail=str(e))


@router.get("/members/{member_id}")
def get_member_detail(member_id: int, db: Session = Depends(get_db)):
    result = member_service.get_member_with_orders(db, member_id)
    if not result:
        raise HTTPException(404, detail="会员不存在")
    member, orders = result
    member["orders"] = orders
    return member


@router.post("/members/{member_id}/points")
def adjust_points(member_id: int, data: PointAdjust, db: Session = Depends(get_db)):
    member = member_service.adjust_points(db, member_id, data)
    if not member:
        raise HTTPException(404, detail="会员不存在")
    return {"points": member.points, "brand": data.brand, "brand_points": data.amount, "message": f"{data.brand}积分{'增加' if data.amount > 0 else '扣减'}{abs(data.amount)}"}


@router.get("/reports/top-members")
def top_members(limit: int = Query(10, ge=1, le=50), db: Session = Depends(get_db)):
    return {"items": member_service.get_top_members(db, limit)}


# ==================== Batch Operations ====================

@router.post("/members/batch-points")
def batch_points(data: BatchPointsRequest, db: Session = Depends(get_db)):
    result = member_service.batch_adjust_points(
        db, data.member_ids, data.brand, data.amount, data.remark,
    )
    return {
        "result": result,
        "message": f"成功处理 {result['success']}/{result['total']} 个会员",
    }


@router.post("/members/batch-coupons")
def batch_coupons(data: BatchCouponRequest, db: Session = Depends(get_db)):
    result = member_service.batch_create_coupons(
        db, data.member_ids, data.brand, data.coupon_name,
        data.expires_at, data.product_id, data.remark,
    )
    if "error" in result:
        raise HTTPException(400, detail=result["error"])
    return {
        "result": result,
        "message": f"成功下发 {result['success']}/{result['total']} 个会员",
    }


@router.get("/members/{member_id}/coupons")
def list_member_coupons(member_id: int, db: Session = Depends(get_db)):
    return {"items": member_service.list_coupons_by_member(db, member_id)}


@router.get("/coupons")
def list_all_coupons(
    brand: str = Query(None),
    status: str = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
):
    items, total = member_service.list_all_coupons(db, brand, status, page, page_size)
    return {"items": items, "total": total, "page": page, "page_size": page_size}


@router.put("/coupons/{coupon_id}/status")
def update_coupon_status(coupon_id: int, status: str = Query(...), db: Session = Depends(get_db)):
    coupon = member_service.update_coupon_status(db, coupon_id, status)
    if not coupon:
        raise HTTPException(404, detail="兑换券不存在")
    return {"coupon": coupon, "message": "状态更新成功"}
