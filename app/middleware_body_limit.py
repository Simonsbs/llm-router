# app/middleware_body_limit.py

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse

class BodySizeLimitMiddleware(BaseHTTPMiddleware):
    """Reject requests with Content-Length > max_content_length."""
    def __init__(self, app, max_content_length: int):
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
