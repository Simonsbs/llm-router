# app/middleware_security.py

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response

# app/middleware_security.py
class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        # Bypass CSP on docs routes
        if request.url.path.startswith(("/docs", "/redoc", "/openapi.json")):
            return await call_next(request)

        response = await call_next(request)
        response.headers["Content-Security-Policy"] = "default-src 'self'"
        return response
