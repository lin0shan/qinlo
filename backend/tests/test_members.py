"""Member tests (P1): CRUD + phone uniqueness + points + ranking."""


def test_create_member(client):
    res = client.post("/api/v1/members", json={
        "name": "王静", "phone": "13800000001", "gender": "女",
        "skin_type": "干性", "tags": "VIP,高复购",
    })
    assert res.status_code == 201


def test_duplicate_phone_rejected(client):
    client.post("/api/v1/members", json={
        "name": "A", "phone": "13800000002",
    })
    res = client.post("/api/v1/members", json={
        "name": "B", "phone": "13800000002",
    })
    assert res.status_code == 409


def test_list_members(client):
    client.post("/api/v1/members", json={"name": "A", "phone": "13800000011"})
    client.post("/api/v1/members", json={"name": "B", "phone": "13800000012"})
    res = client.get("/api/v1/members")
    assert res.status_code == 200
    assert res.json()["total"] == 2


def test_search_member_by_phone(client):
    client.post("/api/v1/members", json={"name": "用户X", "phone": "13800000099"})
    res = client.get("/api/v1/members?keyword=13800000099")
    assert res.json()["total"] == 1


def test_update_member(client):
    client.post("/api/v1/members", json={"name": "旧名", "phone": "13800000021"})
    res = client.put("/api/v1/members/1", json={"name": "新名", "skin_type": "油性"})
    assert res.status_code == 200

    res = client.get("/api/v1/members/1")
    data = res.json()
    assert data["name"] == "新名"
    assert data["skin_type"] == "油性"


def test_adjust_points(client):
    client.post("/api/v1/members", json={"name": "积分测试", "phone": "13800000031"})
    # 增加 500
    client.post("/api/v1/members/1/points", json={"amount": 500})
    res = client.get("/api/v1/members/1")
    assert res.json()["points"] == 500

    # 扣减 100
    client.post("/api/v1/members/1/points", json={"amount": -100})
    res = client.get("/api/v1/members/1")
    assert res.json()["points"] == 400


def test_member_detail_with_orders(client):
    """会员详情含消费记录"""
    client.post("/api/v1/members", json={"name": "消费会员", "phone": "13800000041"})
    client.post("/api/v1/products", json={
        "name": "测试品", "barcode": "BH99001", "spec": "x",
        "category": "护肤", "unit": "瓶", "cost_price": 10, "retail_price": 50,
    })
    client.post("/api/v1/suppliers", json={"name": "供", "phone": "13901"})
    client.post("/api/v1/purchase-orders", json={
        "supplier_id": 1,
        "items": [{"product_id": 1, "quantity": 10, "unit_price": 10}],
    })
    client.post("/api/v1/sale-orders", json={
        "member_id": 1,
        "items": [{"product_id": 1, "quantity": 3, "unit_price": 50}],
    })
    client.post("/api/v1/sale-orders", json={
        "member_id": 1,
        "items": [{"product_id": 1, "quantity": 1, "unit_price": 50}],
    })

    res = client.get("/api/v1/members/1")
    data = res.json()
    assert data["total_spent"] == 200  # 150 + 50
    assert len(data["orders"]) == 2


def test_top_members(client):
    client.post("/api/v1/members", json={"name": "高消费", "phone": "13800000051"})
    client.post("/api/v1/members", json={"name": "低消费", "phone": "13800000052"})

    client.post("/api/v1/products", json={
        "name": "P", "barcode": "BH99002", "spec": "x",
        "category": "护肤", "unit": "瓶", "cost_price": 1, "retail_price": 100,
    })
    client.post("/api/v1/suppliers", json={"name": "S"})
    client.post("/api/v1/purchase-orders", json={
        "supplier_id": 1,
        "items": [{"product_id": 1, "quantity": 100, "unit_price": 1}],
    })
    client.post("/api/v1/sale-orders", json={
        "member_id": 1, "items": [{"product_id": 1, "quantity": 10, "unit_price": 100}],
    })
    client.post("/api/v1/sale-orders", json={
        "member_id": 2, "items": [{"product_id": 1, "quantity": 2, "unit_price": 100}],
    })

    res = client.get("/api/v1/reports/top-members?limit=2")
    top = res.json()["items"]
    assert top[0]["total_spent"] > top[1]["total_spent"]
