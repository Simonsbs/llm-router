# app/middleware_body_limit.py

"""
Custom middleware to enforce a maximum HTTP request body size.

This helps protect the service from:
- DoS attacks using oversized payloads
- Accidental overloads from client misuse
- Excessive memory consumption during parsing

Used in combination with FastAPI + Starlette's middleware system.

🧠 Why this matters:
LLMs can receive huge inputs, so setting boundaries is critical for performance and safety.
"""

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse


class BodySizeLimitMiddleware(BaseHTTPMiddleware):
    """
    Rejects any request where the Content-Length exceeds `max_content_length`.

    Returns HTTP 413 (Payload Too Large) if the limit is exceeded.

    Example usage:
        app.add_middleware(BodySizeLimitMiddleware, max_content_length=1_048_576)  # 1MB
    """
    def __init__(self, app, max_content_length: int):
        """
        Args:
            app: ASGI application instance.
            max_content_length (int): Max content length in bytes.
        """
        super().__init__(app)
        self.max_content_length = max_content_length

    async def dispatch(self, request: Request, call_next):
        content_length = request.headers.get("content-length")

        if content_length and int(content_length) > self.max_content_length:
            return JSONResponse(
                status_code=413,
                content={"detail": "Request body too large"}
            )

        return await call_next(request)
