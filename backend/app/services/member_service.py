from typing import Optional
from datetime import datetime

from sqlalchemy.orm import Session
from sqlalchemy import func, or_
from app.models.member import Member, MemberPoints, MemberCoupon
from app.models.order import SaleOrder, SaleOrderItem
from app.models.product import Product
from app.schemas.member import MemberCreate, MemberUpdate, PointAdjust
from app.logging import ops_log


def _get_brand_points_batch(db: Session, member_ids: list[int]) -> dict[int, dict]:
    """批量获取会员各品牌积分"""
    if not member_ids:
        return {}
    records = db.query(MemberPoints).filter(MemberPoints.member_id.in_(member_ids)).all()
    result = {}
    for r in records:
        if r.member_id not in result:
            result[r.member_id] = {}
        result[r.member_id][r.brand] = r.points
    return result


def _enrich_members(db: Session, members: list) -> list:
    """为会员列表附加 brand_points（批量查询）"""
    ids = [m.id for m in members]
    brand_points_map = _get_brand_points_batch(db, ids)
    result = []
    for m in members:
        d = {
            "id": m.id, "name": m.name, "phone": m.phone,
            "gender": m.gender, "birthday": m.birthday,
            "skin_type": m.skin_type, "tags": m.tags,
            "total_spent": m.total_spent or 0, "points": m.points or 0,
            "brand_points": brand_points_map.get(m.id, {}),
            "remark": m.remark, "created_at": m.created_at, "updated_at": m.updated_at,
        }
        result.append(d)
    return result


def list_members(
    db: Session,
    keyword: Optional[str] = None,
    tags: Optional[str] = None,
    page: int = 1,
    page_size: int = 20,
):
    q = db.query(Member)
    if keyword:
        q = q.filter(
            or_(Member.name.ilike(f"%{keyword}%"), Member.phone.ilike(f"%{keyword}%"))
        )
    if tags:
        for t in tags.split(","):
            q = q.filter(Member.tags.ilike(f"%{t.strip()}%"))

    total = q.count()
    items = q.order_by(Member.updated_at.desc()).offset((page - 1) * page_size).limit(page_size).all()
    return _enrich_members(db, items), total


def get_member(db: Session, member_id: int) -> Optional[Member]:
    return db.query(Member).filter(Member.id == member_id).first()


def create_member(db: Session, data: MemberCreate) -> Member:
    try:
        existing = db.query(Member).filter(Member.phone == data.phone).first()
        if existing:
            raise ValueError("手机号已存在")
        member = Member(**data.model_dump())
        db.add(member)
        db.commit()
        db.refresh(member)
        ops_log.info("member_created", member_id=member.id, phone=member.phone)
        return member
    except Exception:
        db.rollback()
        raise


def update_member(db: Session, member_id: int, data: MemberUpdate) -> Optional[Member]:
    try:
        member = get_member(db, member_id)
        if not member:
            return None
        update_data = data.model_dump(exclude_unset=True)
        if "phone" in update_data and update_data["phone"] != member.phone:
            existing = db.query(Member).filter(Member.phone == update_data["phone"]).first()
            if existing:
                raise ValueError("手机号已被其他会员使用")
        for key, value in update_data.items():
            setattr(member, key, value)
        db.commit()
        db.refresh(member)
        return member
    except Exception:
        db.rollback()
        raise


def adjust_points(db: Session, member_id: int, data: PointAdjust) -> Optional[Member]:
    try:
        member = get_member(db, member_id)
        if not member:
            return None

        # Update brand-specific points
        mp = db.query(MemberPoints).filter(
            MemberPoints.member_id == member_id,
            MemberPoints.brand == data.brand,
        ).first()
        if not mp:
            mp = MemberPoints(member_id=member_id, brand=data.brand, points=0)
            db.add(mp)
        mp.points += data.amount
        if mp.points < 0:
            mp.points = 0

        # Sync total points
        total = db.query(func.sum(MemberPoints.points)).filter(
            MemberPoints.member_id == member_id
        ).scalar() or 0
        member.points = total

        db.commit()
        db.refresh(member)
        ops_log.info("points_adjusted", member_id=member_id, brand=data.brand, amount=data.amount, result=member.points)
        return member
    except Exception:
        db.rollback()
        raise


def get_member_with_orders(db: Session, member_id: int):
    member = get_member(db, member_id)
    if not member:
        return None

    member_data = {
        "id": member.id, "name": member.name, "phone": member.phone,
        "gender": member.gender, "birthday": member.birthday,
        "skin_type": member.skin_type, "tags": member.tags,
        "total_spent": member.total_spent or 0, "points": member.points or 0,
        "brand_points": _get_brand_points_batch(db, [member_id]).get(member_id, {}),
        "remark": member.remark, "created_at": member.created_at, "updated_at": member.updated_at,
    }

    orders = (
        db.query(SaleOrder)
        .filter(SaleOrder.member_id == member_id, SaleOrder.status != "已退货")
        .order_by(SaleOrder.created_at.desc())
        .limit(50)
        .all()
    )

    # 批量查所有订单项的商品
    all_product_ids = [i.product_id for o in orders for i in o.items]
    product_map = {}
    if all_product_ids:
        products = db.query(Product).filter(Product.id.in_(all_product_ids)).all()
        product_map = {p.id: p.name for p in products}

    order_list = []
    for o in orders:
        items = []
        for i in o.items:
            items.append({
                "product_name": product_map.get(i.product_id, ""),
                "quantity": i.quantity,
                "unit_price": i.unit_price,
            })
        order_list.append({
            "id": o.id,
            "total_amount": o.total_amount,
            "actual_amount": o.actual_amount,
            "discount": o.discount,
            "items": items,
            "created_at": o.created_at.isoformat() if o.created_at else None,
        })

    return member_data, order_list


def get_top_members(db: Session, limit: int = 10):
    members = (
        db.query(Member)
        .order_by(Member.total_spent.desc())
        .limit(limit)
        .all()
    )
    return [
        {
            "id": m.id, "name": m.name, "phone": m.phone[-4:],
            "total_spent": m.total_spent or 0, "points": m.points or 0,
        }
        for m in members
    ]


# ==================== Batch Points ====================

def batch_adjust_points(db: Session, member_ids: list, brand: str, amount: int, remark: str = None) -> dict:
    """批量给会员调整积分（逐条 savepoint 保护）"""
    success = 0
    failed = []
    for mid in member_ids:
        try:
            with db.begin_nested():
                member = get_member(db, mid)
                if not member:
                    failed.append({"member_id": mid, "reason": "会员不存在"})
                    continue

                mp = db.query(MemberPoints).filter(
                    MemberPoints.member_id == mid,
                    MemberPoints.brand == brand,
                ).first()
                if not mp:
                    mp = MemberPoints(member_id=mid, brand=brand, points=0)
                    db.add(mp)
                mp.points += amount
                if mp.points < 0:
                    mp.points = 0

                total = db.query(func.sum(MemberPoints.points)).filter(
                    MemberPoints.member_id == mid
                ).scalar() or 0
                member.points = total
                success += 1
        except Exception as e:
            failed.append({"member_id": mid, "reason": str(e)})

    db.commit()
    ops_log.info("batch_points", member_count=len(member_ids), success=success, brand=brand, amount=amount)
    return {"success": success, "total": len(member_ids), "failed": failed}


# ==================== Coupons ====================

def batch_create_coupons(db: Session, member_ids: list, brand: str, coupon_name: str,
                         expires_at: str, product_id: int = None, remark: str = None) -> dict:
    """批量给会员下发兑换券（逐条 savepoint 保护）"""
    success = 0
    failed = []
    try:
        expire_dt = datetime.fromisoformat(expires_at)
    except (ValueError, TypeError):
        return {"success": 0, "total": len(member_ids), "failed": [{"reason": "过期日期格式无效，请使用 ISO 格式如 2026-12-31"}]}

    for mid in member_ids:
        try:
            with db.begin_nested():
                member = get_member(db, mid)
                if not member:
                    failed.append({"member_id": mid, "reason": "会员不存在"})
                    continue
                coupon = MemberCoupon(
                    member_id=mid, brand=brand, coupon_name=coupon_name,
                    product_id=product_id, status="有效", expires_at=expire_dt, remark=remark,
                )
                db.add(coupon)
                success += 1
        except Exception as e:
            failed.append({"member_id": mid, "reason": str(e)})

    db.commit()
    ops_log.info("batch_coupons", member_count=len(member_ids), success=success, brand=brand, coupon=coupon_name)
    return {"success": success, "total": len(member_ids), "failed": failed}


def list_coupons_by_member(db: Session, member_id: int) -> list:
    """获取会员的所有兑换券"""
    coupons = (
        db.query(MemberCoupon)
        .filter(MemberCoupon.member_id == member_id)
        .order_by(MemberCoupon.created_at.desc())
        .all()
    )
    return _enrich_coupons(db, coupons)


def list_all_coupons(db: Session, brand: str = None, status: str = None,
                     page: int = 1, page_size: int = 50) -> tuple:
    """分页查询兑换券（全量）"""
    q = db.query(MemberCoupon)
    if brand:
        q = q.filter(MemberCoupon.brand == brand)
    if status:
        q = q.filter(MemberCoupon.status == status)
    total = q.count()
    coupons = q.order_by(MemberCoupon.expires_at.asc()).offset(
        (page - 1) * page_size).limit(page_size).all()
    return _enrich_coupons(db, coupons), total


def _enrich_coupons(db: Session, coupons: list) -> list:
    """为兑换券附加会员名、手机号、商品名（批量查询）"""
    if not coupons:
        return []

    # Batch query members
    member_ids = list({c.member_id for c in coupons})
    members = db.query(Member).filter(Member.id.in_(member_ids)).all() if member_ids else []
    member_map = {m.id: m for m in members}

    # Batch lookup products
    product_ids = list({c.product_id for c in coupons if c.product_id})
    products = db.query(Product).filter(Product.id.in_(product_ids)).all() if product_ids else []
    product_map = {p.id: p.name for p in products}

    result = []
    for c in coupons:
        m = member_map.get(c.member_id)
        result.append({
            "id": c.id, "member_id": c.member_id,
            "member_name": m.name if m else "-",
            "member_phone": m.phone if m else "-",
            "brand": c.brand, "coupon_name": c.coupon_name,
            "product_id": c.product_id, "product_name": product_map.get(c.product_id),
            "status": c.status,
            "expires_at": c.expires_at.isoformat() if c.expires_at else None,
            "used_at": c.used_at.isoformat() if c.used_at else None,
            "remark": c.remark,
            "created_at": c.created_at.isoformat() if c.created_at else None,
        })
    return result


def update_coupon_status(db: Session, coupon_id: int, status: str) -> Optional[dict]:
    """更新兑换券状态（已兑换/已过期）"""
    try:
        coupon = db.query(MemberCoupon).filter(MemberCoupon.id == coupon_id).first()
        if not coupon:
            return None
        coupon.status = status
        if status == "已兑换":
            coupon.used_at = datetime.now()
        db.commit()
        return _enrich_coupons(db, [coupon])[0]
    except Exception:
        db.rollback()
        raise
