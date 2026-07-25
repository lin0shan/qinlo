"""Order tests (P0): sale orders / purchase orders / member + points."""


def _setup(client):
    client.post("/api/v1/products", json={
        "name": "商品A", "barcode": "BH00000021", "spec": "30ml",
        "category": "护肤", "unit": "瓶", "cost_price": 50, "retail_price": 100,
    })
    client.post("/api/v1/suppliers", json={
        "name": "供应商", "contact": "李四", "phone": "13800000002",
    })
    client.post("/api/v1/members", json={
        "name": "会员A", "phone": "13900000001", "gender": "女",
    })


def test_create_sale_order(client):
    """创建销售单 → 自动扣库存"""
    _setup(client)
    client.post("/api/v1/purchase-orders", json={
        "supplier_id": 1,
        "items": [{"product_id": 1, "quantity": 20, "unit_price": 50}],
    })

    res = client.post("/api/v1/sale-orders", json={
        "items": [{"product_id": 1, "quantity": 3, "unit_price": 100}],
        "discount": 10,
    })
    assert res.status_code == 201
    # 实收 = 3*100 - 10 = 290
    assert res.json()["actual_amount"] == 290


def test_sale_with_member_adds_points(client):
    """关联会员 → 累加消费金额+积分"""
    _setup(client)
    client.post("/api/v1/purchase-orders", json={
        "supplier_id": 1,
        "items": [{"product_id": 1, "quantity": 10, "unit_price": 50}],
    })

    res = client.post("/api/v1/sale-orders", json={
        "member_id": 1,
        "items": [{"product_id": 1, "quantity": 2, "unit_price": 100}],
    })
    assert res.status_code == 201

    # 会员积分应增加 200
    res = client.get("/api/v1/members/1")
    member = res.json()
    assert member["total_spent"] == 200
    assert member["points"] == 200


def test_create_purchase_order(client):
    """创建采购单 → 生成库存流水"""
    _setup(client)

    res = client.post("/api/v1/purchase-orders", json={
        "supplier_id": 1,
        "items": [{"product_id": 1, "quantity": 100, "unit_price": 45}],
    })
    assert res.status_code == 201
    assert res.json()["total_amount"] == 4500


def test_purchase_return(client):
    """采购退货 → 库存扣减"""
    _setup(client)
    client.post("/api/v1/purchase-orders", json={
        "supplier_id": 1,
        "items": [{"product_id": 1, "quantity": 30, "unit_price": 50}],
    })

    res = client.post("/api/v1/purchase-orders/1/return")
    assert res.status_code == 200

    # 库存归零
    res = client.get("/api/v1/inventory")
    assert res.json()["items"][0]["current_stock"] == 0


def test_sale_order_list(client):
    """销售单列表"""
    _setup(client)
    client.post("/api/v1/purchase-orders", json={
        "supplier_id": 1,
        "items": [{"product_id": 1, "quantity": 5, "unit_price": 50}],
    })
    client.post("/api/v1/sale-orders", json={
        "items": [{"product_id": 1, "quantity": 1, "unit_price": 100}],
    })

    res = client.get("/api/v1/sale-orders")
    assert res.status_code == 200
    data = res.json()
    assert data["total"] >= 1
    # 详情可查
    oid = data["items"][0]["id"]
    res = client.get(f"/api/v1/sale-orders/{oid}")
    assert res.status_code == 200
