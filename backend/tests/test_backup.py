"""Backup & restore tests (P2)."""


def test_create_backup(client):
    """创建备份"""
    res = client.post("/api/v1/backup")
    assert res.status_code == 200
    data = res.json()
    assert data["message"] == "备份完成"
    assert "file_name" in data


def test_backup_list(client):
    """备份列表"""
    client.post("/api/v1/backup")
    res = client.get("/api/v1/backup/list")
    assert res.status_code == 200
    assert len(res.json()) >= 1


def test_download_404_without_backup(client):
    """Returns 404 when no backup files exist (isolated from other tests)."""
    import shutil, os
    from app.config import settings
    # 清空备份目录
    if settings.BACKUP_DIR.exists():
        for f in settings.BACKUP_DIR.glob("*.db"):
            os.remove(f)
    res = client.get("/api/v1/backup/download")
    assert res.status_code == 404


def test_restore_invalid_file_rejected(client):
    """无效文件恢复被拒绝"""
    res = client.post("/api/v1/restore", files={"file": ("test.txt", b"not a db")})
    assert res.status_code == 400


def test_restore_valid_backup(client):
    """恢复有效备份后数据一致"""
    # 写入一些数据
    client.post("/api/v1/products", json={
        "name": "备份测试品", "barcode": "BH99030", "spec": "30ml",
        "category": "护肤", "unit": "瓶", "cost_price": 10, "retail_price": 20,
    })
    client.post("/api/v1/suppliers", json={"name": "S"})
    client.post("/api/v1/members", json={"name": "M", "phone": "13900000002"})

    # 备份
    res = client.post("/api/v1/backup")
    assert res.status_code == 200
    backup_file = res.json()["file_name"]

    # 下载备份文件
    res = client.get(f"/api/v1/backup/download?file_name={backup_file}")
    assert res.status_code == 200
    backup_data = res.content

    # 上传恢复
    res = client.post("/api/v1/restore", files={"file": (backup_file, backup_data)})
    assert res.status_code == 200

    # 数据仍在
    res = client.get("/api/v1/products?keyword=备份测试品")
    assert res.json()["total"] == 1
