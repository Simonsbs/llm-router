# app/dependencies.py

from fastapi import Depends
from app.adapters.adapter import Adapter
from app.schemas import ChatRequest, EmbeddingRequest

async def get_chat_adapter(
    req: ChatRequest
) -> Adapter:
    """
    Provide the right Adapter based on req.stream.
    """
    kind = "stream_chat" if req.stream else "chat"
    return Adapter(kind, req.dict())

async def get_embedding_adapter(
    req: EmbeddingRequest
) -> Adapter:
    """
    Provide an Adapter for embedding endpoints.
    """
    return Adapter("embed", req.dict())
