"""Authentication middleware.

Cloud mode: requires X-Access-Key on every request (except whitelist).
Local mode: requires X-Local-Token for write operations from non-localhost IPs.
"""
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse
from fastapi import Request
from app.config import settings


class AuthMiddleware(BaseHTTPMiddleware):
    """Authentication guard supporting two deployment modes."""

    WRITE_METHODS = {"POST", "PUT", "PATCH", "DELETE"}

    @staticmethod
    def _is_localhost(request: Request) -> bool:
        host = request.client.host if request.client else ""
        return host in ("127.0.0.1", "::1", "localhost")

    async def dispatch(self, request: Request, call_next):
        path = request.url.path
        # Whitelist: health check, docs, OpenAPI schema, static uploads
        if path.startswith(("/api/v1/health", "/docs", "/openapi.json", "/uploads")):
            return await call_next(request)

        # Cloud mode: verify ACCESS_KEY globally
        if settings.DEPLOY_MODE == "cloud":
            access_key = request.headers.get("X-Access-Key") or request.query_params.get("key")
            if access_key != settings.ACCESS_KEY:
                return JSONResponse(status_code=401, content={"detail": "Unauthorized: valid ACCESS_KEY required"})
            return await call_next(request)

        # Local mode: require LOCAL_TOKEN for non-localhost write operations
        if settings.LOCAL_TOKEN and request.method in self.WRITE_METHODS and not self._is_localhost(request):
            token = request.headers.get("X-Local-Token") or request.query_params.get("token")
            if token != settings.LOCAL_TOKEN:
                return JSONResponse(status_code=401, content={"detail": "Unauthorized: valid LOCAL_TOKEN required"})

        return await call_next(request)
