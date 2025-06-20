# app/middleware_security.py

"""
Security middleware to inject basic HTTP headers for added protection.

Currently implements a `Content-Security-Policy` (CSP) header to restrict
content sources to the application’s own origin (`'self'`), reducing the risk
of XSS attacks in browser environments.

This middleware:
- Applies security headers to all routes
- Skips Swagger and Redoc docs routes to avoid breaking their UI

🛡️ Note: This is not a full security suite. CSP is a helpful addition,
but you may still want tools like Helmet (Node), ModSecurity, or AWS WAF for full protection.
"""

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """
    Injects HTTP headers like Content-Security-Policy into all HTTP responses.

    Skips FastAPI's documentation endpoints (`/docs`, `/redoc`, `/openapi.json`)
    to preserve their built-in functionality (which pulls external assets).
    """
    async def dispatch(self, request: Request, call_next):
        # Skip CSP enforcement for auto-generated docs UI
        if request.url.path.startswith(("/docs", "/redoc", "/openapi.json")):
            return await call_next(request)

        response: Response = await call_next(request)
        response.headers["Content-Security-Policy"] = "default-src 'self'"
        return response
