# app/dependencies.py

"""
Dependency injection utilities for FastAPI endpoints in the SimonGPT LLM Router.

These helper functions are used with FastAPI's `Depends()` to dynamically
construct the appropriate `Adapter` based on the request type.

The adapter acts as a runtime strategy pattern wrapper to select
the correct backend provider (e.g., OpenAI, Ollama, DeepSeek).

These functions are lightweight and only perform minimal logic to
determine the type of adapter needed per incoming request.

📦 Modules Used:
- `ChatRequest` and `EmbeddingRequest` define the expected request schemas.
- `Adapter` encapsulates logic for selecting and routing to the correct LLM provider.
"""

from fastapi import Depends
from app.adapters.adapter import Adapter
from app.schemas import ChatRequest, EmbeddingRequest


async def get_chat_adapter(
    req: ChatRequest
) -> Adapter:
    """
    FastAPI dependency that returns a chat Adapter instance.

    Selects the adapter type based on whether streaming is enabled
    (e.g., "stream_chat" vs "chat").

    Args:
        req (ChatRequest): The parsed request body model for chat.

    Returns:
        Adapter: A runtime adapter instance for executing the chat logic.
    """
    kind = "stream_chat" if req.stream else "chat"
    return Adapter(kind, req.dict())


async def get_embedding_adapter(
    req: EmbeddingRequest
) -> Adapter:
    """
    FastAPI dependency that returns an embedding Adapter instance.

    Args:
        req (EmbeddingRequest): The parsed request body model for embeddings.

    Returns:
        Adapter: A runtime adapter instance for computing vector embeddings.
    """
    return Adapter("embed", req.dict())
