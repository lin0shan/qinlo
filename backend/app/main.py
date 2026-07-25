"""FastAPI application entry point.

Serves both the API and the production frontend build from the same process.
In production mode the Vue SPA is hosted on the same host/port as the API.
"""
import os
import sys
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

from app.config import settings, BASE_DIR, APP_ROOT
from app.database import init_db
from app.logging import logger
from app.middleware.auth import AuthMiddleware
from app.middleware.logging import LoggingMiddleware

app = FastAPI(
    title="个人商业助手",
    description="Beauty industry inventory management + CRM all-in-one tool",
    version="1.0.0",
    docs_url="/docs",
)

# Resolve frontend dist directory (compatible with PyInstaller packaging)
if getattr(sys, 'frozen', False):
    _FRONTEND_DIST = (APP_ROOT / "frontend" / "dist").resolve()
else:
    _FRONTEND_DIST = (BASE_DIR / ".." / "frontend" / "dist").resolve()
_is_production = _FRONTEND_DIST.exists() and _FRONTEND_DIST.is_dir()

# CORS — only needed in dev mode (Vite dev server on separate port)
if _is_production:
    pass
else:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[
            "https://localhost:5173", "https://localhost:5174",
            "http://localhost:5173", "http://localhost:5174",
            "https://192.168.1.120:5173", "https://192.168.1.120:5174",
            "http://192.168.1.120:5173", "http://192.168.1.120:5174",
        ],
        allow_methods=["*"],
        allow_headers=["*"],
    )

# Custom middleware
app.add_middleware(LoggingMiddleware)
app.add_middleware(AuthMiddleware)

# Static files — uploaded product images
settings.UPLOADS_DIR.mkdir(parents=True, exist_ok=True)
app.mount("/uploads", StaticFiles(directory=str(settings.UPLOADS_DIR)), name="uploads")

# Production mode: serve frontend build artifacts
if _is_production:
    app.mount("/assets", StaticFiles(directory=str(_FRONTEND_DIST / "assets")), name="assets")
    _index_html = _FRONTEND_DIST / "index.html"
    if _index_html.exists():
        @app.get("/")
        async def serve_frontend():
            return FileResponse(str(_index_html))

# Register routers — try/except per module so one failure doesn't block others
import logging
import traceback
_err_log = logging.getLogger("errors")

_ROUTER_MODULES = [
    ("products", "products.router"),
    ("orders", "orders.router"),
    ("inventory", "inventory.router"),
    ("members", "members.router"),
    ("shipments", "shipments.router"),
    ("sync", "sync.router"),
    ("reports", "reports.router"),
    ("backup", "backup.router"),
    ("settings_router", "settings_router.router"),
    ("import_router", "import_router.router"),
]

for mod_name, router_attr in _ROUTER_MODULES:
    try:
        mod = __import__(f"app.routers.{mod_name}", fromlist=["router"])
        app.include_router(getattr(mod, "router"))
    except Exception:
        _err_log.error(
            f"Failed to register router: {mod_name}",
            exc_info=True,
            extra={"traceback": traceback.format_exc()},
        )


@app.on_event("startup")
def on_startup():
    """Application startup: create dirs, init DB, start scheduler, print local token."""
    try:
        settings.DATA_DIR.mkdir(parents=True, exist_ok=True)
        settings.BACKUP_DIR.mkdir(parents=True, exist_ok=True)
        init_db()
        from app.routers.settings_router import init_scheduler
        init_scheduler()
        if settings.DEPLOY_MODE == "local" and settings.LOCAL_TOKEN:
            print(f"\n  [LOCAL TOKEN] {settings.LOCAL_TOKEN}\n")
        logger.info("app_started", deploy_mode=settings.DEPLOY_MODE)
    except Exception:
        _err_log.error("Startup initialization failed", exc_info=True,
                        extra={"traceback": traceback.format_exc()})
        raise


@app.get("/api/v1/health")
def health_check():
    """Return server health status."""
    return {"status": "ok", "deploy_mode": settings.DEPLOY_MODE}
