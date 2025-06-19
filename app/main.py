import logging
from typing import Dict, List

from fastapi import FastAPI, HTTPException, Depends
from pydantic import BaseModel, Field
from fastapi.responses import StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from langsmith.middleware import TracingMiddleware
from asgi_correlation_id import CorrelationIdMiddleware

from app.logging_config import configure_logging
from app.middlewares import LoggingMiddleware
from app.security import verify_api_key
from app.middleware_security import SecurityHeadersMiddleware
from app.middleware_body_limit import BodySizeLimitMiddleware
from app.adapters.adapter import Adapter

# ─── Init ───────────────────────────────────────────────────────────────────────
configure_logging()

app = FastAPI(
    title="SimonGPT LLM Router",
    version="0.1.0",
    description="Dynamically routes /v1/chat/completions to Ollama, OpenAI, etc.",
    dependencies=[Depends(verify_api_key)],
)

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

# ─── Endpoints ──────────────────────────────────────────────────────────────────
@app.post("/v1/chat/completions")
async def chat(req: ChatRequest):
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
async def embeddings(req: EmbeddingRequest):
    payload = req.dict()
    adapter = Adapter("embed", payload)

    try:
        return await adapter.embed(req.input)
    except Exception:
        logging.getLogger("router").exception("embedding error")
        raise HTTPException(500, detail="Embedding failed")
