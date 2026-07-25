from typing import Optional
from sqlalchemy.orm import Session
from sqlalchemy import func, or_
from app.models.product import Product, ProductStatus
from app.models.inventory import InventoryLog
from app.schemas.product import ProductCreate, ProductUpdate


def get_product(db: Session, product_id: int) -> Optional[Product]:
    return db.query(Product).filter(Product.id == product_id).first()


def list_products(
    db: Session,
    keyword: Optional[str] = None,
    category: Optional[str] = None,
    brand: Optional[str] = None,
    status: Optional[str] = None,
    page: int = 1,
    page_size: int = 20,
):
    q = db.query(Product)
    if keyword:
        q = q.filter(
            or_(
                Product.name.ilike(f"%{keyword}%"),
                Product.barcode.ilike(f"%{keyword}%"),
                Product.sku_code.ilike(f"%{keyword}%"),
                Product.brand.ilike(f"%{keyword}%"),
            )
        )
    if category:
        q = q.filter(Product.category == category)
    if brand:
        q = q.filter(Product.brand == brand)
    if status:
        q = q.filter(Product.status == status)

    total = q.count()
    items = q.order_by(Product.updated_at.desc()).offset((page - 1) * page_size).limit(page_size).all()

    # Fill live inventory stock
    product_ids = [p.id for p in items]
    stock_map = _get_stock_map(db, product_ids)

    return items, total, stock_map


def create_product(db: Session, data: ProductCreate) -> Product:
    try:
        product_data = data.model_dump()
        # Auto-generate SKU code if not provided
        if not product_data.get("sku_code"):
            product_data["sku_code"] = _generate_sku_code(db, product_data.get("brand", ""))
        # Convert empty barcode to None to avoid unique constraint conflict
        if not product_data.get("barcode"):
            product_data["barcode"] = None
        product = Product(**product_data)
        db.add(product)
        db.flush()  # Get product.id for code generation
        # Auto-generate product code if not provided: BH + 8-digit ID
        if product.barcode is None:
            product.barcode = f"BH{product.id:08d}"
            db.flush()
        db.commit()
        db.refresh(product)
        return product
    except Exception:
        db.rollback()
        raise


def update_product(db: Session, product_id: int, data: ProductUpdate) -> Optional[Product]:
    product = get_product(db, product_id)
    if not product:
        return None
    update_data = data.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(product, key, value)
    db.commit()
    db.refresh(product)
    return product


def set_product_status(db: Session, product_id: int, status: str) -> Optional[Product]:
    product = get_product(db, product_id)
    if not product:
        return None
    product.status = status
    db.commit()
    db.refresh(product)
    return product


def check_barcode_exists(db: Session, barcode: str, exclude_id: Optional[int] = None) -> bool:
    q = db.query(Product).filter(Product.barcode == barcode)
    if exclude_id:
        q = q.filter(Product.id != exclude_id)
    return q.first() is not None


def _get_stock_map(db: Session, product_ids: list[int]) -> dict[int, int]:
    """批量查询实时库存"""
    if not product_ids:
        return {}
    rows = (
        db.query(InventoryLog.product_id, func.sum(InventoryLog.change_quantity))
        .filter(InventoryLog.product_id.in_(product_ids))
        .group_by(InventoryLog.product_id)
        .all()
    )
    return {row[0]: (row[1] or 0) for row in rows}


def get_product_stock(db: Session, product_id: int) -> int:
    result = (
        db.query(func.sum(InventoryLog.change_quantity))
        .filter(InventoryLog.product_id == product_id)
        .scalar()
    )
    return result or 0


def _brand_to_prefix(brand: str) -> str:
    """Convert brand name to SKU prefix using pinyin initials; defaults to 'GEN'."""
    if not brand or not brand.strip():
        return "GEN"
    # Chinese brand -> pinyin initial mapping (extend as needed)
    brand_map = {
        "赫莲娜": "HLN",
    }
    return brand_map.get(brand.strip(), "GEN")


def _generate_sku_code(db: Session, brand: str) -> str:
    """Auto-generate the next SKU code for a given brand prefix."""
    prefix = _brand_to_prefix(brand)
    # Query max existing sequence number under this prefix
    result = (
        db.query(Product.sku_code)
        .filter(Product.sku_code.like(f"{prefix}-%"))
        .order_by(Product.sku_code.desc())
        .first()
    )
    if result and result[0]:
        last_num = int(result[0].split("-")[1])
        next_num = last_num + 1
    else:
        next_num = 1
    return f"{prefix}-{next_num:04d}"
