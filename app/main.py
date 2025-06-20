# app/main.py

"""
Main entry point for the SimonGPT LLM Router FastAPI service.

This file defines:
- Service startup and healthchecks
- CORS, security, and custom middlewares
- JWT-based token issuing
- Adapter-based routing to multiple LLM backends (e.g., OpenAI, Ollama, DeepSeek)
- Prometheus metrics for observability
- Rate-limited RESTful API endpoints for /chat/completions and /embeddings

🧠 This service dynamically routes incoming requests to appropriate LLM providers using
adapter logic while enforcing security, performance, and observability standards.
"""

import os
import sys
import time
import json
import jwt
import httpx
import logging
import datetime

from fastapi import (
    FastAPI, Request, Response, status, HTTPException, Body, Depends
)
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse, JSONResponse

from app.config import settings
from app.logging_config import configure_logging
from app.middlewares import LoggingMiddleware
from app.middleware_security import SecurityHeadersMiddleware
from app.middleware_body_limit import BodySizeLimitMiddleware
from app.security import verify_jwt
from app.dependencies import get_chat_adapter, get_embedding_adapter
from app.exceptions import AdapterError
from app.adapters.adapter import Adapter

# ─── Tracing & Request Correlation ─────────────────────────────────────────────
from asgi_correlation_id import CorrelationIdMiddleware
from langsmith.middleware import TracingMiddleware

# ─── Rate Limiting ─────────────────────────────────────────────────────────────
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.middleware import SlowAPIMiddleware
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

# ─── Metrics / Prometheus ──────────────────────────────────────────────────────
from prometheus_client import (
    Counter, Histogram, CollectorRegistry,
    generate_latest, CONTENT_TYPE_LATEST, multiprocess
)

# ───────────────────────────────────────────────────────────────────────────────
# Prometheus Metrics — track request volume and latency per method + path
# ───────────────────────────────────────────────────────────────────────────────
REQUEST_COUNT = Counter(
    "http_requests_total",
    "Total HTTP requests",
    ["method", "endpoint", "http_status"]
)

REQUEST_LATENCY = Histogram(
    "http_request_duration_seconds",
    "HTTP request latency",
    ["method", "endpoint"]
)

# ───────────────────────────────────────────────────────────────────────────────
# Application Startup
# ───────────────────────────────────────────────────────────────────────────────
configure_logging()

app = FastAPI(
    title="SimonGPT LLM Router",
    version="0.1.0",
    description="Dynamically routes /v1/chat/completions to Ollama, OpenAI, DeepSeek, etc."
)


@app.on_event("startup")
async def startup_healthchecks():
    """
    On startup, validate LLM provider connectivity to avoid silent boot errors.
    - Always check OpenAI.
    - Optionally check Ollama if default model routes to it.
    """
    async with httpx.AsyncClient(timeout=5.0) as client:
        try:
            await client.get(
                f"{settings.openai_api_base}/v1/models",
                headers={"Authorization": f"Bearer {os.getenv('OPENAI_API_KEY', '')}"}
            )
        except Exception as e:
            print(f"🔥 OpenAI healthcheck failed: {e}", file=sys.stderr)
            raise RuntimeError("OpenAI is unreachable at startup") from e

        if settings.default_chat_model.startswith("ollama"):
            try:
                await client.get(f"{settings.ollama_url}/api/health")
            except Exception as e:
                logging.getLogger("router").warning(f"Ollama healthcheck warning: {e}")

# ───────────────────────────────────────────────────────────────────────────────
# Global Exception Handling
# ───────────────────────────────────────────────────────────────────────────────
@app.exception_handler(AdapterError)
async def handle_adapter_error(request: Request, exc: AdapterError):
    """
    Gracefully return structured JSON errors for known adapter failures.
    """
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail}
    )

# ───────────────────────────────────────────────────────────────────────────────
# Middleware Stack
# ───────────────────────────────────────────────────────────────────────────────
app.add_middleware(CorrelationIdMiddleware)
app.add_middleware(LoggingMiddleware)
app.add_middleware(SecurityHeadersMiddleware)
app.add_middleware(BodySizeLimitMiddleware, max_content_length=1_048_576)  # 1MB max

try:
    app.add_middleware(TracingMiddleware)
except ImportError:
    pass

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=False,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "X-API-Key"],
    max_age=3600,
)

# ───────────────────────────────────────────────────────────────────────────────
# Rate Limiting
# ───────────────────────────────────────────────────────────────────────────────
limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
app.add_middleware(SlowAPIMiddleware)

# ───────────────────────────────────────────────────────────────────────────────
# Prometheus Middleware
# ───────────────────────────────────────────────────────────────────────────────
@app.middleware("http")
async def metrics_middleware(request: Request, call_next):
    start = time.time()
    response = await call_next(request)
    elapsed = time.time() - start

    REQUEST_LATENCY.labels(method=request.method, endpoint=request.url.path).observe(elapsed)
    REQUEST_COUNT.labels(
        method=request.method,
        endpoint=request.url.path,
        http_status=str(response.status_code),
    ).inc()

    return response

@app.get("/metrics", include_in_schema=False)
async def metrics():
    """
    Prometheus endpoint for scraping runtime stats.
    Supports both single- and multi-process environments.
    """
    mp_dir = os.getenv("PROMETHEUS_MULTIPROC_DIR")
    if mp_dir and os.path.isdir(mp_dir):
        registry = CollectorRegistry()
        multiprocess.MultiProcessCollector(registry)
        data = generate_latest(registry)
    else:
        data = generate_latest()
    return Response(content=data, media_type=CONTENT_TYPE_LATEST)

# ───────────────────────────────────────────────────────────────────────────────
# Health Probes
# ───────────────────────────────────────────────────────────────────────────────
@app.get("/healthz", tags=["health"])
async def healthz():
    """
    Kubernetes-style liveness probe — basic internal health check.
    No external dependencies.
    """
    return {"status": "ok"}


@app.get("/readyz", tags=["health"])
async def readyz():
    """
    Kubernetes-style readiness probe — verifies LLM backends are reachable.
    """
    errors = {}
    async with httpx.AsyncClient(timeout=2.0) as client:
        try:
            await client.get(
                f"{settings.openai_api_base}/v1/models",
                headers={"Authorization": f"Bearer {os.getenv('OPENAI_API_KEY','')}"}
            )
        except Exception as e:
            errors["openai"] = str(e)

        if settings.default_chat_model.startswith("ollama"):
            try:
                await client.get(f"{settings.ollama_url}/api/health")
            except Exception as e:
                errors["ollama"] = str(e)

    if errors:
        return Response(
            content=json.dumps({"ready": False, "errors": errors}),
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            media_type="application/json"
        )

    return {"ready": True}

# ───────────────────────────────────────────────────────────────────────────────
# JWT Token Issuer Endpoint
# ───────────────────────────────────────────────────────────────────────────────
@app.post("/v1/token")
@limiter.limit(settings.rate_limit_token)
async def get_token(request: Request, api_key: str = Body(..., embed=True)):
    """
    Exchange a valid API key for a short-lived JWT token.
    """
    if api_key != settings.llm_router_api_key:
        raise HTTPException(403, detail="Invalid API key")

    now = datetime.datetime.utcnow()
    exp = now + datetime.timedelta(minutes=60)
    token = jwt.encode(
        {"sub": "router-client", "exp": exp},
        settings.jwt_secret_key,
        algorithm="HS256"
    )

    return {"access_token": token, "token_type": "bearer"}

# ───────────────────────────────────────────────────────────────────────────────
# /v1/chat/completions
# ───────────────────────────────────────────────────────────────────────────────
@app.post("/v1/chat/completions")
@limiter.limit(settings.rate_limit_chat)
async def chat(
    request: Request,
    _: dict = Depends(verify_jwt),
    adapter: Adapter = Depends(get_chat_adapter)
):
    """
    Chat interface. Uses adapters to route to OpenAI/Ollama/DeepSeek.
    Supports streaming and non-streaming responses.
    """
    payload     = adapter.payload
    messages    = payload["messages"]
    temperature = payload.get("temperature", 0.7)
    max_tokens  = payload.get("max_tokens", 1024)
    stream      = payload.get("stream", False)

    if stream:
        async def event_gen():
            async for chunk in adapter.chat_stream(messages, temperature, max_tokens):
                yield f"data: {chunk}\n\n"
            yield "data: [DONE]\n\n"

        return StreamingResponse(event_gen(), media_type="text/event-stream")

    return await adapter.chat(messages, temperature, max_tokens)

# ───────────────────────────────────────────────────────────────────────────────
# /v1/embeddings
# ───────────────────────────────────────────────────────────────────────────────
@app.post("/v1/embeddings")
@limiter.limit(settings.rate_limit_embed)
async def embeddings(
    request: Request,
    _: dict = Depends(verify_jwt),
    adapter: Adapter = Depends(get_embedding_adapter)
):
    """
    Embedding interface. Routes to the correct vector backend.
    """
    inputs = adapter.payload["input"]
    try:
        return await adapter.embed(inputs)
    except Exception:
        logging.getLogger("router").exception("embedding error")
        raise HTTPException(500, detail="Embedding failed")
