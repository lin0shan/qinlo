"""Structured logging setup with separate streams: app / operations / errors.

Uses structlog for structured (JSON) log output and bridges standard library logging.
"""
import structlog
import logging
from pathlib import Path
from app.config import settings

settings.LOGS_DIR.mkdir(parents=True, exist_ok=True)


def setup_logging():
    """Configure structlog with three log streams: app, operations, errors."""

    timestamper = structlog.processors.TimeStamper(fmt="iso", utc=False)

    # --- App log (app.log): structured JSON for all general log entries ---
    app_file = logging.FileHandler(settings.LOGS_DIR / "app.log", encoding="utf-8")
    app_file.setLevel(logging.INFO)

    structlog.configure(
        processors=[
            structlog.stdlib.add_log_level,
            structlog.stdlib.add_logger_name,
            timestamper,
            structlog.processors.JSONRenderer(),
        ],
        wrapper_class=structlog.stdlib.BoundLogger,
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )

    # --- Stdlib logging bridge ---
    root_logger = logging.getLogger()
    root_logger.handlers.clear()
    root_logger.addHandler(app_file)
    root_logger.setLevel(logging.INFO)

    # --- Operations log (operations.log): audit trail for data mutations ---
    ops_handler = logging.FileHandler(settings.LOGS_DIR / "operations.log", encoding="utf-8")
    ops_handler.setLevel(logging.INFO)
    ops_logger = logging.getLogger("operations")
    ops_logger.handlers.clear()
    ops_logger.addHandler(ops_handler)
    ops_logger.setLevel(logging.INFO)
    ops_logger.propagate = False

    # --- Error log (error.log): fatal/unexpected errors ---
    err_handler = logging.FileHandler(settings.LOGS_DIR / "error.log", encoding="utf-8")
    err_handler.setLevel(logging.ERROR)
    err_logger = logging.getLogger("errors")
    err_logger.handlers.clear()
    err_logger.addHandler(err_handler)
    err_logger.setLevel(logging.ERROR)
    err_logger.propagate = False

    return structlog.get_logger()


logger = setup_logging()
ops_log = structlog.get_logger("operations")

