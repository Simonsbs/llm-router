import importlib
import logging
from typing import Dict, List, Any

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

from langchain_core.runnables import RunnableLambda
from app.adapters.runnables import router_chain

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
    model: str = Field(..., examples=["openai:gpt-4o", "ollama:llama3"])
    messages: List[Dict[str, str]]
    temperature: float | None = 0.7
    max_tokens: int | None = 1024
    stream: bool | None = False

# ─── Helper ─────────────────────────────────────────────────────────────────────
def _load_adapter(model_id: str):
    """
    Fallback for streaming: load provider adapter by prefix.
    Default provider = 'ollama'.
    """
    if ":" in model_id:
        provider, model_name = model_id.split(":", 1)
    else:
        provider, model_name = "ollama", model_id

    try:
        mod = importlib.import_module(f"app.adapters.{provider}_adapter")
        return mod.get_adapter(model_name)
    except ModuleNotFoundError:
        raise HTTPException(400, detail=f"Provider '{provider}' not supported")

# ─── Endpoints ──────────────────────────────────────────────────────────────────
@app.post("/v1/chat/completions")
async def chat(req: ChatRequest):
    inputs = {
        "model": req.model,
        "messages": req.messages,
        "temperature": req.temperature,
        "max_tokens": req.max_tokens,
    }

    if req.stream:
        # Streaming path still uses direct adapter for chunked SSE
        adapter = _load_adapter(req.model)

        async def event_gen():
            async for chunk in adapter.chat_stream(
                req.messages, req.temperature, req.max_tokens
            ):
                yield f"data: {chunk}\n\n"
            yield "data: [DONE]\n\n"

        return StreamingResponse(event_gen(), media_type="text/event-stream")

    # Non‐streaming: invoke the LangChain router dynamically
    result = await router_chain.ainvoke(inputs)
    return result

class EmbeddingRequest(BaseModel):
    model: str = Field(..., examples=["ollama:bge-m3"])
    input: List[str] = Field(..., examples=[["What is Simon B. Stirling known for?"]])

@app.post("/v1/embeddings")
async def embeddings(req: EmbeddingRequest):
    adapter = _load_adapter(req.model)
    logger = logging.getLogger("router")

    try:
        result = await adapter.embed(req.input)
        return result
    except Exception as e:
        logger.exception("embedding error")
        raise HTTPException(500, detail="Embedding failed")
