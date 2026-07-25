"""Product CRUD tests."""


def test_create_product(client):
    res = client.post("/api/v1/products", json={
        "name": "兰蔻精华液", "barcode": "BH00000001", "spec": "30ml",
        "category": "护肤", "unit": "瓶", "cost_price": 180, "retail_price": 299,
        "safety_stock": 5,
    })
    assert res.status_code == 201
    assert res.json()["message"] == "商品创建成功"


def test_list_products(client):
    client.post("/api/v1/products", json={
        "name": "测试商品", "barcode": "BH00000002", "spec": "100ml",
        "category": "护肤", "unit": "瓶", "cost_price": 50, "retail_price": 99,
    })
    res = client.get("/api/v1/products")
    assert res.status_code == 200
    data = res.json()
    assert data["total"] >= 1
    assert len(data["items"]) >= 1


def test_search_by_name(client):
    client.post("/api/v1/products", json={
        "name": "小黑瓶精华", "barcode": "BH00000003", "spec": "50ml",
        "category": "护肤", "unit": "瓶", "cost_price": 300, "retail_price": 580,
    })
    res = client.get("/api/v1/products?keyword=小黑瓶")
    assert res.status_code == 200
    data = res.json()
    assert data["total"] == 1
    assert data["items"][0]["name"] == "小黑瓶精华"


def test_search_by_barcode(client):
    client.post("/api/v1/products", json={
        "name": "SK-II神仙水", "barcode": "BH00000004", "spec": "230ml",
        "category": "护肤", "unit": "瓶", "cost_price": 800, "retail_price": 1299,
    })
    res = client.get("/api/v1/products?keyword=BH00000004")
    assert res.status_code == 200
    data = res.json()
    assert len(data["items"]) == 1


def test_update_product(client):
    client.post("/api/v1/products", json={
        "name": "旧名称", "barcode": "BH00000005", "spec": "10ml",
        "category": "护肤", "unit": "瓶", "cost_price": 10, "retail_price": 20,
    })
    res = client.put("/api/v1/products/1", json={"name": "新名称", "retail_price": 25})
    assert res.status_code == 200

    res = client.get("/api/v1/products?keyword=新名称")
    assert res.json()["items"][0]["retail_price"] == 25


def test_toggle_status(client):
    client.post("/api/v1/products", json={
        "name": "可停售商品", "barcode": "BH00000006", "spec": "30ml",
        "category": "护肤", "unit": "瓶", "cost_price": 10, "retail_price": 30,
    })
    res = client.patch("/api/v1/products/1/status?status=停售")
    assert res.status_code == 200

    res = client.get("/api/v1/products?keyword=可停售")
    assert res.json()["items"][0]["status"] == "停售"


def test_duplicate_barcode_rejected(client):
    client.post("/api/v1/products", json={
        "name": "A", "barcode": "BH00000007", "spec": "x",
        "category": "护肤", "unit": "瓶", "cost_price": 1, "retail_price": 2,
    })
    res = client.post("/api/v1/products", json={
        "name": "B", "barcode": "BH00000007", "spec": "y",
        "category": "护肤", "unit": "瓶", "cost_price": 1, "retail_price": 2,
    })
    assert res.status_code == 409
