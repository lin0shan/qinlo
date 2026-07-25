"""Sync tests (P1): batch submit, versioning, no-op."""


def test_sync_version(client):
    """版本号接口正常"""
    res = client.get("/api/v1/sync/version")
    assert res.status_code == 200
    data = res.json()
    assert "version" in data
    assert "stats" in data


def test_sync_empty_batch(client):
    """空操作批量提交"""
    res = client.post("/api/v1/sync/batch", json={
        "operations": [],
        "client_id": "test-client",
    })
    assert res.status_code == 200
    data = res.json()
    assert data["summary"]["total"] == 0


def test_sync_create_sale_order(client):
    """通过同步接口创建销售单"""
    # 准备数据
    client.post("/api/v1/products", json={
        "name": "同步商品", "barcode": "BH99010", "spec": "30ml",
        "category": "护肤", "unit": "瓶", "cost_price": 50, "retail_price": 100,
    })
    client.post("/api/v1/suppliers", json={"name": "同步供应商"})
    client.post("/api/v1/purchase-orders", json={
        "supplier_id": 1,
        "items": [{"product_id": 1, "quantity": 10, "unit_price": 50}],
    })

    # 通过同步接口创建销售单
    res = client.post("/api/v1/sync/batch", json={
        "operations": [{
            "action": "sale_order_create",
            "payload": {
                "items": [{"product_id": 1, "quantity": 2, "unit_price": 100}],
                "discount": 0,
            },
            "client_id": "offline-001",
        }],
    })
    assert res.status_code == 200
    data = res.json()
    assert data["summary"]["success"] == 1

    # 销售单列表应可见
    res = client.get("/api/v1/sale-orders")
    assert res.json()["total"] >= 1


def test_sync_duplicate_member_rejected(client):
    """同步创建重复会员被拒绝"""
    client.post("/api/v1/members", json={"name": "已有", "phone": "13900000001"})

    res = client.post("/api/v1/sync/batch", json={
        "operations": [{
            "action": "member_create",
            "payload": {"name": "重复", "phone": "13900000001"},
            "client_id": "dup-001",
        }],
    })
    assert res.status_code == 200
    data = res.json()
    # 同步报错但接口本身 200
    assert data["summary"]["fail"] >= 1
