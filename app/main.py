import logging
from app.config import settings
import datetime
import json
import jwt
import time
import os
import httpx
import sys
from fastapi import Body
from fastapi import FastAPI, Response, status
import httpx, os

from fastapi import FastAPI, HTTPException, Depends
from starlette.requests import Request
from fastapi.responses import StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from langsmith.middleware import TracingMiddleware
from asgi_correlation_id import CorrelationIdMiddleware
from app.adapters.adapter import Adapter

from app.logging_config import configure_logging
from app.middlewares import LoggingMiddleware
from app.security import verify_jwt
from app.middleware_security import SecurityHeadersMiddleware
from app.middleware_body_limit import BodySizeLimitMiddleware
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware
from app.dependencies import get_chat_adapter, get_embedding_adapter
from fastapi import Request
from fastapi.responses import JSONResponse
from app.exceptions import AdapterError
from prometheus_client import (
    Counter,
    Histogram,
    CollectorRegistry,
    generate_latest,
    CONTENT_TYPE_LATEST,
    multiprocess,
)
from fastapi.responses import Response

# ─── Prometheus Metrics ────────────────────────────────────────────────────────
REQUEST_COUNT = Counter(
    "http_requests_total",
    "Total HTTP requests",
    ["method", "endpoint", "http_status"],
)
REQUEST_LATENCY = Histogram(
    "http_request_duration_seconds",
    "HTTP request latency",
    ["method", "endpoint"],
)

# ─── Init ───────────────────────────────────────────────────────────────────────
configure_logging()

app = FastAPI(
    title="SimonGPT LLM Router",
    version="0.1.0",
    description="Dynamically routes /v1/chat/completions to Ollama, OpenAI, etc.",
)

@app.on_event("startup")
async def startup_healthchecks():
    async with httpx.AsyncClient(timeout=5.0) as client:
        # Always check OpenAI…
        try:
            await client.get(
                f"{settings.openai_api_base}/v1/models",
                headers={"Authorization": f"Bearer {os.getenv('OPENAI_API_KEY','')}"}
            )
        except Exception as e:
            print(f"🔥 OpenAI healthcheck failed: {e}", file=sys.stderr)
            raise RuntimeError("OpenAI is unreachable at startup") from e

        # …but only check Ollama if your default model is an Ollama model
        if settings.default_chat_model.startswith("ollama"):
            try:
                await client.get(f"{settings.ollama_url}/api/health")
            except Exception as e:
                logging.getLogger("router").warning(f"Ollama healthcheck warning: {e}")

# ─── Global Exception Handler ───────────────────────────────────────────────────
@app.exception_handler(AdapterError)
async def handle_adapter_error(request: Request, exc: AdapterError):
    """
    Catch any AdapterError raised in handlers or adapters
    and return a clean JSON response.
    """
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail},
    )

# ─── Rate Limiting ──────────────────────────────────────────────────────────────
limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
app.add_middleware(SlowAPIMiddleware)


# ─── Middleware ─────────────────────────────────────────────────────────────────
app.add_middleware(CorrelationIdMiddleware)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=False,            # set True once you lock down allow_origins
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "X-API-Key"],
    max_age=3600,
)

app.add_middleware(LoggingMiddleware)
app.add_middleware(SecurityHeadersMiddleware)
app.add_middleware(BodySizeLimitMiddleware, max_content_length=1_048_576)

try:
    app.add_middleware(TracingMiddleware)
except ImportError:
    pass

# ─── Metrics Middleware ────────────────────────────────────────────────────────
@app.middleware("http")
async def metrics_middleware(request: Request, call_next):
    start = time.time()
    response = await call_next(request)
    elapsed = time.time() - start

    # record histogram and counter
    REQUEST_LATENCY.labels(method=request.method, endpoint=request.url.path).observe(elapsed)
    REQUEST_COUNT.labels(
        method=request.method,
        endpoint=request.url.path,
        http_status=str(response.status_code),
    ).inc()

    return response

# ─── Metrics Endpoint ─────────────────────────────────────────────────────────
@app.get("/metrics", include_in_schema=False)
async def metrics():
    """
    Expose Prometheus metrics.
    """
    mp_dir = os.getenv("PROMETHEUS_MULTIPROC_DIR")
    if mp_dir and os.path.isdir(mp_dir):
        # multi-process mode: collect from the shared dir
        registry = CollectorRegistry()
        multiprocess.MultiProcessCollector(registry)
        data = generate_latest(registry)
    else:
        # single-process: use the default REGISTRY, which already has our counters
        data = generate_latest()
    return Response(content=data, media_type=CONTENT_TYPE_LATEST)


# ─── Health Check ───────────────────────────────────────────────────────────────
@app.get("/healthz", tags=["health"])
async def healthz():
    # “I am alive” – no external calls
    return {"status": "ok"}

@app.get("/readyz", tags=["health"])
async def readyz():
    """
    “Am I ready to serve traffic?”
     – OpenAI must be up
     – Ollama only if it’s in your default routing
    """
    errors = {}
    async with httpx.AsyncClient(timeout=2.0) as client:
        # 1) OpenAI
        try:
            await client.get(
                f"{settings.openai_api_base}/v1/models",
                headers={"Authorization": f"Bearer {os.getenv('OPENAI_API_KEY','')}"}
            )
        except Exception as e:
            errors["openai"] = str(e)

        # 2) Ollama (only if you might route to it)
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

# ─── API Key Authentication ──────────────────────────────────────────────────────
@app.post("/v1/token")
@limiter.limit(settings.rate_limit_token)
async def get_token(request: Request ,api_key: str = Body(..., embed=True)):
    """
    Exchange a valid API key for a JWT (valid for 60 minutes).
    """
    if api_key != settings.llm_router_api_key:
        raise HTTPException(403, detail="Invalid API key")

    now   = datetime.datetime.utcnow()
    exp   = now + datetime.timedelta(minutes=60)
    token = jwt.encode(
        {"sub": "router-client", "exp": exp}, 
        settings.jwt_secret_key, 
        algorithm="HS256"
    )

    return {"access_token": token, "token_type": "bearer"}


# ─── Endpoints ──────────────────────────────────────────────────────────────────
@app.post("/v1/chat/completions")
@limiter.limit(settings.rate_limit_chat)
async def chat(
    request: Request,
    _: dict = Depends(verify_jwt),
    adapter: Adapter = Depends(get_chat_adapter),
):
    # unpack once from adapter.payload
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


@app.post("/v1/embeddings")
@limiter.limit(settings.rate_limit_embed)
async def embeddings(
    request: Request,
    _: dict = Depends(verify_jwt),
    adapter: Adapter = Depends(get_embedding_adapter),
):
    inputs = adapter.payload["input"]
    try:
        return await adapter.embed(inputs)
    except Exception:
        logging.getLogger("router").exception("embedding error")
        raise HTTPException(500, detail="Embedding failed")
