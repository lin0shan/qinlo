"""pytest configuration — uses in-memory SQLite for isolation."""
import os
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
os.environ["DATABASE_URL"] = "sqlite:///:memory:"

import pytest
from sqlalchemy import create_engine, event, text
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

import app.database as db

# 使用 StaticPool 确保所有连接共享同一个 :memory: 数据库
_test_engine = create_engine(
    "sqlite://",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)

@event.listens_for(_test_engine, "connect")
def _pragma(dbapi_conn, rec):
    c = dbapi_conn.cursor()
    c.execute("PRAGMA foreign_keys=ON")
    c.close()

db.engine = _test_engine
db.SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=_test_engine)

# 导入模型
from app.models.product import Product  # noqa: E402, F401
from app.models.supplier import Supplier  # noqa: E402, F401
from app.models.order import PurchaseOrder, PurchaseOrderItem, SaleOrder, SaleOrderItem  # noqa: E402, F401
from app.models.shipment import Shipment  # noqa: E402, F401
from app.models.inventory import InventoryLog  # noqa: E402, F401
from app.models.member import Member  # noqa: E402, F401
from app.models.backup import BackupLog  # noqa: E402, F401

db.Base.metadata.create_all(bind=_test_engine)

from app.main import app  # noqa: E402
app.router.on_startup.clear()


@pytest.fixture(scope="function")
def client():
    db.Base.metadata.create_all(bind=_test_engine)

    def _override():
        s = db.SessionLocal()
        try:
            yield s
        finally:
            s.close()

    app.dependency_overrides[db.get_db] = _override
    from fastapi.testclient import TestClient
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()

    with _test_engine.connect() as conn:
        for table in reversed(db.Base.metadata.sorted_tables):
            conn.execute(text(f"DELETE FROM {table.name}"))
        conn.commit()
