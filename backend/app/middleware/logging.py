"""Request/response logging middleware.

Logs method, path, status code, duration, and client IP for every request.
"""
import time
from starlette.middleware.base import BaseHTTPMiddleware
from fastapi import Request
from app.logging import logger as app_logger


class LoggingMiddleware(BaseHTTPMiddleware):
    """Record request metadata to the structured logger."""

    async def dispatch(self, request: Request, call_next):
        start = time.time()
        response = await call_next(request)
        duration = round((time.time() - start) * 1000, 2)

        app_logger.info(
            "request",
            method=request.method,
            path=request.url.path,
            status=response.status_code,
            duration_ms=duration,
            client_ip=request.client.host if request.client else "unknown",
        )
        return response
