"""System settings API."""

import json
import shutil
import os
from datetime import datetime
from pathlib import Path

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from apscheduler.schedulers.background import BackgroundScheduler

from app.config import settings
from app.logging import ops_log

router = APIRouter(prefix="/api/v1", tags=["系统设置"])

SETTINGS_FILE = settings.DATA_DIR / "app_settings.json"

DEFAULT_SETTINGS = {
    "shop_name": "个人商业助手",
    "low_stock_threshold": 10,
    "backup_auto_enabled": False,
    "backup_interval_hours": 24,
    "barcode_prefix": "BH",
}

_scheduler: BackgroundScheduler | None = None


def _load_settings() -> dict:
    if SETTINGS_FILE.exists():
        try:
            return json.loads(SETTINGS_FILE.read_text(encoding="utf-8"))
        except Exception:
            pass
    return dict(DEFAULT_SETTINGS)


def _save_settings(data: dict):
    SETTINGS_FILE.parent.mkdir(parents=True, exist_ok=True)
    SETTINGS_FILE.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


class SettingsUpdate(BaseModel):
    shop_name: str | None = None
    low_stock_threshold: int | None = None
    backup_auto_enabled: bool | None = None
    backup_interval_hours: int | None = None
    barcode_prefix: str | None = None


@router.get("/settings")
def get_settings():
    """获取系统设置"""
    return _load_settings()


@router.put("/settings")
def update_settings(data: SettingsUpdate):
    """更新系统设置"""
    current = _load_settings()
    for key, value in data.model_dump(exclude_unset=True).items():
        if value is not None:
            current[key] = value
    _save_settings(current)
    ops_log.info("settings_updated", **{k: v for k, v in data.model_dump(exclude_unset=True).items()})

    # Update scheduled backup job
    _update_backup_schedule(current)
    return current


def _do_auto_backup():
    """定时自动备份"""
    db_path = settings.DATA_DIR / "business.db"
    if not db_path.exists():
        return
    backup_dir = settings.BACKUP_DIR
    backup_dir.mkdir(parents=True, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = backup_dir / f"auto_backup_{ts}.db"
    shutil.copy2(db_path, backup_path)
    ops_log.info("auto_backup_done", file=str(backup_path))

    # Keep the latest 50 backups, delete old ones
    all_backups = sorted(backup_dir.glob("*.db"), key=os.path.getmtime)
    for old in all_backups[:-50]:
        old.unlink(missing_ok=True)


def _update_backup_schedule(config: dict):
    global _scheduler
    if _scheduler:
        try:
            _scheduler.remove_job("auto_backup")
        except Exception:
            pass

    if config.get("backup_auto_enabled"):
        if not _scheduler:
            _scheduler = BackgroundScheduler()
            _scheduler.start()
        hours = config.get("backup_interval_hours", 24)
        _scheduler.add_job(_do_auto_backup, "interval", hours=hours, id="auto_backup")


def init_scheduler():
    """应用启动时初始化定时备份"""
    config = _load_settings()
    _update_backup_schedule(config)
