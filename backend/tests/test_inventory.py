"""Inventory tests (P0): purchase stock-in / sale stock-out / return restore / check adjust."""


def _create_product_and_supplier(client):
    """辅助：创建商品和供应商"""
    client.post("/api/v1/products", json={
        "name": "测试商品", "barcode": "BH00000011", "spec": "30ml",
        "category": "护肤", "unit": "瓶", "cost_price": 100, "retail_price": 200,
        "safety_stock": 10,
    })
    client.post("/api/v1/suppliers", json={
        "name": "测试供应商", "contact": "张三", "phone": "13800000001",
    })


def test_purchase_increases_stock(client):
    """采购入库 → 库存增加"""
    _create_product_and_supplier(client)

    # 初始库存为 0
    res = client.get("/api/v1/inventory")
    assert res.json()["items"][0]["current_stock"] == 0

    # 采购入库 50 件
    res = client.post("/api/v1/purchase-orders", json={
        "supplier_id": 1,
        "items": [{"product_id": 1, "quantity": 50, "unit_price": 100}],
    })
    assert res.status_code == 201

    # 验证库存
    res = client.get("/api/v1/inventory")
    assert res.json()["items"][0]["current_stock"] == 50


def test_sale_decreases_stock(client):
    """销售出库 → 库存减少"""
    _create_product_and_supplier(client)

    # 先入库 50
    client.post("/api/v1/purchase-orders", json={
        "supplier_id": 1,
        "items": [{"product_id": 1, "quantity": 50, "unit_price": 100}],
    })

    # 销售 10 件
    res = client.post("/api/v1/sale-orders", json={
        "items": [{"product_id": 1, "quantity": 10, "unit_price": 200}],
        "discount": 0,
    })
    assert res.status_code == 201

    # 库存应为 40
    res = client.get("/api/v1/inventory")
    assert res.json()["items"][0]["current_stock"] == 40


def test_sale_return_restores_stock(client):
    """销售退货 → 库存恢复"""
    _create_product_and_supplier(client)

    client.post("/api/v1/purchase-orders", json={
        "supplier_id": 1,
        "items": [{"product_id": 1, "quantity": 30, "unit_price": 100}],
    })
    client.post("/api/v1/sale-orders", json={
        "items": [{"product_id": 1, "quantity": 10, "unit_price": 200}],
    })

    # 退货
    res = client.post("/api/v1/sale-orders/1/return")
    assert res.status_code == 200

    # 库存恢复
    res = client.get("/api/v1/inventory")
    assert res.json()["items"][0]["current_stock"] == 30


def test_inventory_check_correction(client):
    """盘点 → 差异修正"""
    _create_product_and_supplier(client)

    client.post("/api/v1/purchase-orders", json={
        "supplier_id": 1,
        "items": [{"product_id": 1, "quantity": 20, "unit_price": 100}],
    })

    # 盘点：实际只有 18 件
    res = client.post("/api/v1/inventory/check", json={
        "items": [{"product_id": 1, "actual_quantity": 18}],
    })
    assert res.status_code == 200

    # 盘点结果：差异 -2
    result = res.json()["items"][0]
    assert result["system_quantity"] == 20
    assert result["actual_quantity"] == 18
    assert result["difference"] == -2

    # 库存修正为 18
    res = client.get("/api/v1/inventory")
    assert res.json()["items"][0]["current_stock"] == 18


def test_inventory_logs_traceable(client):
    """库存流水可追溯"""
    _create_product_and_supplier(client)

    client.post("/api/v1/purchase-orders", json={
        "supplier_id": 1,
        "items": [{"product_id": 1, "quantity": 5, "unit_price": 100}],
    })
    client.post("/api/v1/sale-orders", json={
        "items": [{"product_id": 1, "quantity": 2, "unit_price": 200}],
    })

    res = client.get("/api/v1/inventory/logs?product_id=1")
    assert res.status_code == 200
    logs = res.json()["items"]
    assert len(logs) == 2
    # 日志按时间倒序: 先销售出库(最新)，再采购入库
    types = [l["change_type"] for l in logs]
    quantities = [l["change_quantity"] for l in logs]
    assert set(types) == {"采购入库", "销售出库"}
    assert set(quantities) == {5, -2}
