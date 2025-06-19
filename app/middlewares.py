import time, uuid, logging
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response
from asgi_correlation_id import correlation_id

class LoggingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        start = time.perf_counter()
        logger = logging.getLogger("router")
        request_id = correlation_id.get() or str(uuid.uuid4())

        try:
            response = await call_next(request)
        except Exception as e:
            duration = (time.perf_counter() - start) * 1000
            logger.exception("unhandled exception",
                extra={
                    "method": request.method,
                    "path": request.url.path,
                    "status": 500,
                    "duration_ms": round(duration, 2),
                    "request_id": request_id,
                }
            )
            raise  # re-raise to let FastAPI handle error response

        duration = (time.perf_counter() - start) * 1000
        logger.info("request completed",
            extra={
                "method": request.method,
                "path": request.url.path,
                "status": response.status_code,
                "duration_ms": round(duration, 2),
                "request_id": request_id,
            }
        )
        return response
