import logging
import os
import datetime
import jwt
from fastapi import Body

from typing import Dict, List

from fastapi import FastAPI, HTTPException, Depends
from starlette.requests import Request
from pydantic import BaseModel, Field
from fastapi.responses import StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from langsmith.middleware import TracingMiddleware
from asgi_correlation_id import CorrelationIdMiddleware

from app.logging_config import configure_logging
from app.middlewares import LoggingMiddleware
from app.security import verify_jwt
from app.middleware_security import SecurityHeadersMiddleware
from app.middleware_body_limit import BodySizeLimitMiddleware
from app.adapters.adapter import Adapter
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware


# ─── Init ───────────────────────────────────────────────────────────────────────
configure_logging()

app = FastAPI(
    title="SimonGPT LLM Router",
    version="0.1.0",
    description="Dynamically routes /v1/chat/completions to Ollama, OpenAI, etc.",
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
    allow_origins=["*"],                # DEV only: switch to your UI origin when ready
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

# ─── Models ─────────────────────────────────────────────────────────────────────
class ChatRequest(BaseModel):
    messages: List[Dict[str, str]]
    temperature: float | None = 0.7
    max_tokens: int | None = 1024
    stream: bool | None = False


# ─── API Key Authentication ──────────────────────────────────────────────────────
API_KEY = os.getenv("LLM_ROUTER_API_KEY")
SECRET      = os.getenv("JWT_SECRET_KEY")
@app.post("/v1/token")
@limiter.limit("10/minute")
async def get_token(request: Request ,api_key: str = Body(..., embed=True)):
    """
    Exchange a valid API key for a JWT (valid for 60 minutes).
    """
    if api_key != API_KEY:
        raise HTTPException(403, detail="Invalid API key")

    now   = datetime.datetime.utcnow()
    exp   = now + datetime.timedelta(minutes=60)
    token = jwt.encode({"sub": "router-client", "exp": exp}, SECRET, algorithm="HS256")

    return {"access_token": token, "token_type": "bearer"}


# ─── Endpoints ──────────────────────────────────────────────────────────────────
@app.post("/v1/chat/completions")
@limiter.limit("30/minute")
async def chat(request: Request, req: ChatRequest,_: dict = Depends(verify_jwt),):
    payload = req.dict()
    adapter = Adapter("stream_chat" if req.stream else "chat", payload)

    if req.stream:
        async def event_gen():
            async for chunk in adapter.chat_stream(
                req.messages, req.temperature, req.max_tokens
            ):
                yield f"data: {chunk}\n\n"
            yield "data: [DONE]\n\n"
        return StreamingResponse(event_gen(), media_type="text/event-stream")

    return await adapter.chat(req.messages, req.temperature, req.max_tokens)

class EmbeddingRequest(BaseModel):
    input: List[str] = Field(..., examples=[["What is Simon B. Stirling known for?"]])

@app.post("/v1/embeddings")
@limiter.limit("60/minute")
async def embeddings(request: Request, req: EmbeddingRequest,_: dict = Depends(verify_jwt),):
    payload = req.dict()
    adapter = Adapter("embed", payload)

    try:
        return await adapter.embed(req.input)
    except Exception:
        logging.getLogger("router").exception("embedding error")
        raise HTTPException(500, detail="Embedding failed")
