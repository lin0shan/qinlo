"""Application configuration via pydantic-settings.

All settings can be overridden via a .env file next to the executable/backend dir.
"""
import sys
import uuid
from pydantic_settings import BaseSettings
from pathlib import Path

BASE_DIR: Path = Path(__file__).resolve().parent.parent


def get_app_root() -> Path:
    """Return the application root directory (compatible with PyInstaller)."""
    if getattr(sys, 'frozen', False):
        # When frozen, the exe lives in app/ subdir; parent is the app root
        return Path(sys.executable).parent.parent
    else:
        # Dev mode: backend/ is the app root
        return BASE_DIR


APP_ROOT: Path = get_app_root()


class Settings(BaseSettings):
    # Deployment mode: local | cloud
    DEPLOY_MODE: str = "local"

    # Database path override (empty = use default path under data/)
    DB_PATH: str = ""

    # Cloud access key (used when DEPLOY_MODE=cloud)
    ACCESS_KEY: str = ""

    # Local auth token for LAN write operations (auto-generated if empty)
    LOCAL_TOKEN: str = ""

    # Image processing
    IMAGE_MAX_WIDTH: int = 800
    IMAGE_QUALITY: int = 80

    # Server
    HOST: str = "0.0.0.0"
    PORT: int = 8000

    @property
    def DATABASE_URL(self) -> str:
        if self.DB_PATH:
            db = self.DB_PATH
        else:
            db = (APP_ROOT / "data" / "business.db").as_posix()
        return f"sqlite:///{db}"

    @property
    def DATA_DIR(self) -> Path:
        return APP_ROOT / "data"

    @property
    def UPLOADS_DIR(self) -> Path:
        return APP_ROOT / "uploads"

    @property
    def LOGS_DIR(self) -> Path:
        return APP_ROOT / "logs"

    @property
    def BACKUP_DIR(self) -> Path:
        return self.DATA_DIR / "backups"

    model_config = {"env_file": ".env", "extra": "ignore"}


settings = Settings()

# Auto-generate local token if in local mode
if settings.DEPLOY_MODE == "local" and not settings.LOCAL_TOKEN:
    settings.LOCAL_TOKEN = uuid.uuid4().hex[:12]
