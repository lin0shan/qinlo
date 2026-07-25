"""Backup & restore API."""

import shutil
import os
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.database import get_db
from app.config import settings
from app.models.backup import BackupLog
from app.logging import ops_log

router = APIRouter(prefix="/api/v1", tags=["备份恢复"])

DB_PATH = settings.DATA_DIR / "business.db"


@router.post("/backup")
def create_backup(db: Session = Depends(get_db)):
    """手动创建备份"""
    settings.BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_name = f"backup_{ts}.db"
    backup_path = settings.BACKUP_DIR / backup_name

    shutil.copy2(DB_PATH, backup_path)
    file_size = os.path.getsize(backup_path)

    log = BackupLog(file_path=str(backup_path), file_size=file_size)
    db.add(log)
    db.commit()

    ops_log.info("backup_created", file=backup_name, size=file_size)
    return {
        "file_name": backup_name,
        "file_size": file_size,
        "created_at": ts,
        "message": "备份完成",
    }


@router.get("/backup/download")
def download_backup(file_name: str = None):
    """下载备份文件（默认最新）"""
    if file_name:
        path = settings.BACKUP_DIR / file_name
    else:
        # Find the latest backup file
        files = sorted(settings.BACKUP_DIR.glob("backup_*.db"), key=os.path.getmtime, reverse=True)
        if not files:
            raise HTTPException(404, detail="没有可用的备份文件")
        path = files[0]

    if not path.exists():
        raise HTTPException(404, detail="备份文件不存在")

    return FileResponse(
        path=str(path),
        media_type="application/octet-stream",
        filename=path.name,
    )


@router.post("/restore")
async def restore_backup(file: UploadFile = File(...), db: Session = Depends(get_db)):
    """上传备份文件并恢复"""
    if not file.filename or not file.filename.endswith(".db"):
        raise HTTPException(400, detail="请上传 .db 备份文件")

    restore_path = settings.DATA_DIR / "restore_temp.db"
    content = await file.read()
    restore_path.write_bytes(content)

    # Verify it is a valid SQLite file
    import sqlite3
    try:
        conn = sqlite3.connect(str(restore_path))
        conn.execute("SELECT count(*) FROM product")
        conn.close()
    except Exception:
        restore_path.unlink(missing_ok=True)
        raise HTTPException(400, detail="无效的备份文件")

    # Replace current database (backup current one first)
    backup_old = settings.DATA_DIR / f"pre_restore_{datetime.now().strftime('%Y%m%d_%H%M%S')}.db"
    shutil.copy2(DB_PATH, backup_old)
    shutil.copy2(restore_path, DB_PATH)
    restore_path.unlink(missing_ok=True)

    ops_log.info("backup_restored", old_backup=str(backup_old))
    return {"message": "数据恢复成功", "old_backup": backup_old.name}


@router.get("/backup/list")
def list_backups(db: Session = Depends(get_db)):
    """备份历史列表"""
    logs = db.query(BackupLog).order_by(BackupLog.created_at.desc()).limit(20).all()
    return [
        {
            "id": l.id,
            "file_name": os.path.basename(l.file_path) if l.file_path else "",
            "file_size": l.file_size,
            "created_at": l.created_at.isoformat() if l.created_at else None,
        }
        for l in logs
    ]
