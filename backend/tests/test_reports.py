"""Reports tests (P1): daily/monthly report accuracy, top-selling ranking."""


def _seed_sales(client):
    client.post("/api/v1/products", json={
        "name": "热销品", "barcode": "BH99020", "spec": "30ml",
        "category": "护肤", "unit": "瓶", "cost_price": 50, "retail_price": 100,
    })
    client.post("/api/v1/products", json={
        "name": "冷门品", "barcode": "BH99021", "spec": "50ml",
        "category": "护肤", "unit": "瓶", "cost_price": 30, "retail_price": 80,
    })
    client.post("/api/v1/suppliers", json={"name": "供应商R"})
    client.post("/api/v1/purchase-orders", json={
        "supplier_id": 1,
        "items": [
            {"product_id": 1, "quantity": 100, "unit_price": 50},
            {"product_id": 2, "quantity": 50, "unit_price": 30},
        ],
    })
    # 热销品卖 10 件，冷门品卖 1 件
    client.post("/api/v1/sale-orders", json={
        "items": [{"product_id": 1, "quantity": 10, "unit_price": 100}],
    })
    client.post("/api/v1/sale-orders", json={
        "items": [{"product_id": 2, "quantity": 1, "unit_price": 80}],
    })


def test_sales_daily_report(client):
    """日报有数据"""
    _seed_sales(client)
    res = client.get("/api/v1/reports/sales?period=daily")
    assert res.status_code == 200
    data = res.json()
    assert data["period"] == "daily"
    assert data["summary"]["total_orders"] >= 2
    assert data["summary"]["total_actual"] > 0


def test_sales_monthly_report(client):
    """月报格式正确"""
    _seed_sales(client)
    res = client.get("/api/v1/reports/sales?period=monthly")
    assert res.status_code == 200
    data = res.json()
    assert data["period"] == "monthly"
    assert len(data["items"]) >= 1


def test_top_products_by_quantity(client):
    """热销排行按销量 — 热销品排第一"""
    _seed_sales(client)
    res = client.get("/api/v1/reports/top-products?limit=5&sort_by=quantity")
    assert res.status_code == 200
    items = res.json()["items"]
    assert len(items) >= 2
    assert items[0]["product_name"] == "热销品"
    assert items[0]["total_quantity"] == 10


def test_top_products_by_amount(client):
    """热销排行按金额"""
    _seed_sales(client)
    res = client.get("/api/v1/reports/top-products?limit=5&sort_by=amount")
    assert res.status_code == 200
    items = res.json()["items"]
    assert items[0]["total_amount"] >= items[-1]["total_amount"]
