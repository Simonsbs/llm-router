# app/middlewares.py

"""
Custom middleware for logging request lifecycle metrics with correlation IDs.

This module defines `LoggingMiddleware`, which logs:
- HTTP method
- Path
- Status code
- Response time (ms)
- Unique request ID (from correlation ID or fallback UUID)

Logs are JSON-structured and emitted to the central logger under "router".

🧠 Purpose:
- Enable traceable observability across distributed systems
- Improve debugging, performance analysis, and error root cause tracking
- Integrate smoothly with log aggregation services like ELK, CloudWatch, etc.
"""

import time
import uuid
import logging

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from asgi_correlation_id import correlation_id


class LoggingMiddleware(BaseHTTPMiddleware):
    """
    Middleware that logs every incoming request and outgoing response,
    including duration and correlation ID (if present).

    Uses `asgi-correlation-id` to propagate request IDs for distributed tracing.
    """

    async def dispatch(self, request: Request, call_next):
        start = time.perf_counter()
        logger = logging.getLogger("router")

        # Use correlation ID if available, otherwise generate a fallback UUID
        request_id = correlation_id.get() or str(uuid.uuid4())

        try:
            response: Response = await call_next(request)
        except Exception as e:
            duration = (time.perf_counter() - start) * 1000
            logger.exception(
                "unhandled exception",
                extra={
                    "method": request.method,
                    "path": request.url.path,
                    "status": 500,
                    "duration_ms": round(duration, 2),
                    "request_id": request_id,
                },
            )
            raise  # re-raise for FastAPI to handle error response

        duration = (time.perf_counter() - start) * 1000
        logger.info(
            "request completed",
            extra={
                "method": request.method,
                "path": request.url.path,
                "status": response.status_code,
                "duration_ms": round(duration, 2),
                "request_id": request_id,
            },
        )
        return response
