"""
Request audit middleware.

Logs mutating requests (POST/PUT/PATCH/DELETE) by authenticated users to
the structured log.  Full AuditLog DB writes are added in the relevant
service methods (auth register/login, wallet track/untrack, etc.) rather
than the middleware, to keep the middleware lightweight and non-blocking.

Also adds standard security response headers on every response.
"""
import time

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

from app.core.logging import get_logger

logger = get_logger(__name__)

_MUTATING_METHODS = frozenset({"POST", "PUT", "PATCH", "DELETE"})
_SECURITY_HEADERS = {
    "X-Content-Type-Options": "nosniff",
    "X-Frame-Options": "DENY",
    "X-XSS-Protection": "1; mode=block",
    "Referrer-Policy": "strict-origin-when-cross-origin",
    "Permissions-Policy": "geolocation=(), microphone=()",
}


class AuditMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next) -> Response:  # type: ignore[override]
        start = time.monotonic()
        response: Response = await call_next(request)
        duration_ms = round((time.monotonic() - start) * 1000, 1)

        # Add security headers to every response
        for header, value in _SECURITY_HEADERS.items():
            response.headers[header] = value

        # Structured audit log for mutating requests
        if request.method in _MUTATING_METHODS:
            logger.info(
                "api_request",
                method=request.method,
                path=request.url.path,
                status=response.status_code,
                duration_ms=duration_ms,
                ip=request.client.host if request.client else None,
            )

        return response
