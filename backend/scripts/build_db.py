"""Initialize database from Excel and generate sample data."""
import sys, os, traceback
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

data_dir = os.path.join(os.path.dirname(__file__), "..", "data")
db_path = os.path.join(data_dir, "business.db")

# Clean up old DB and WAL files
for f in [db_path, db_path + "-wal", db_path + "-shm"]:
    try:
        if os.path.exists(f):
            os.remove(f)
            print(f"deleted: {f}")
    except Exception as e:
        print(f"skip: {f} ({e})")

try:
    from app.database import engine, Base, SessionLocal, settings
    from app.models import *
    from datetime import datetime
    import pandas as pd

    print(f"DB URL: {settings.DATABASE_URL}")
    Base.metadata.create_all(bind=engine)
    print("Tables created")

    xlsx = os.path.join(data_dir, "商品SKU规格对照表_new.xlsx")
    df = pd.read_excel(xlsx)
    print(f"XLSX rows: {len(df)}")

    CATEGORY_MAP = {"护肤": "护肤", "skincare": "护肤", "彩妆": "彩妆", "makeup": "彩妆", "香水": "香水", "工具": "工具"}
    UNIT_MAP = {"瓶": "瓶", "支": "支", "盒": "盒", "个": "个", "片": "片", "bottle": "瓶"}

    db = SessionLocal()
    count = 0
    for _, row in df.iterrows():
        name = row.get("商品名称")
        if pd.isna(name) or not str(name).strip():
            continue
        name = str(name).strip()

        sku = str(row.get("SKU编码", "")).strip() if not pd.isna(row.get("SKU编码")) else ""
        barcode = str(row.get("店内编码", "")).strip() if not pd.isna(row.get("店内编码")) else ""
        spec = str(row.get("规格", "")).strip() if not pd.isna(row.get("规格")) else ""
        brand = str(row.get("品牌", "")).strip() if not pd.isna(row.get("品牌")) else ""
        cat = str(row.get("分类", "")).strip() if not pd.isna(row.get("分类")) else ""
        unit = str(row.get("单位", "")).strip() if not pd.isna(row.get("单位")) else ""

        if brand == "-":
            brand = ""
        if spec == "-":
            spec = ""

        try:
            from app.models.product import Product
            p = Product(
                name=name,
                barcode=barcode if barcode else None,
                sku_code=sku if sku else None,
                spec=spec if spec else "",
                brand=brand if brand else "",
                category=CATEGORY_MAP.get(cat, cat if cat else "护肤"),
                unit=UNIT_MAP.get(unit, unit if unit else "瓶"),
                cost_price=0,
                retail_price=0,
                safety_stock=10,
                status="在售",
                created_at=datetime.now(),
                updated_at=datetime.now(),
            )
            db.add(p)
            count += 1
        except Exception as e:
            print(f"ERROR row: {sku} {name}: {e}")

    db.commit()
    db.close()
    print(f"Done: {count} products")

except Exception as e:
    print(f"FATAL: {e}")
    traceback.print_exc()
