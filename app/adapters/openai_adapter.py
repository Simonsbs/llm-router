# app/adapters/openai_adapter.py

"""
OpenAI Adapter for SimonGPT LLM Router.

Implements the BaseAdapter interface to interact with OpenAI's chat and embedding APIs
via the official `openai` Python SDK.

Supports:
- Streaming and non-streaming chat completions
- Text embedding generation

All operations use the `AsyncOpenAI` client and handle OpenAI-specific exceptions.
"""

import os
import uuid
import json
import logging
from typing import List, Dict, Any, AsyncIterator
from openai import AsyncOpenAI, OpenAIError

from .base import BaseAdapter
from app.exceptions import AdapterError


logger = logging.getLogger("app.adapters.openai_adapter")

# Global client instance
client = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))


class OpenAIAdapter(BaseAdapter):
    """
    Adapter for OpenAI models (e.g., gpt-3.5, gpt-4, embeddings).
    """

    def __init__(self, model_name: str):
        # Strip prefix if passed as "openai:gpt-4" — keep just model ID
        self.model_name = model_name.split(":", 1)[1] if ":" in model_name else model_name

    async def chat(
        self,
        messages: List[Dict[str, str]],
        temperature: float | None = 0.7,
        max_tokens: int | None = 1024
    ) -> Dict[str, Any]:
        """
        Perform a non-streaming chat completion with OpenAI.

        Returns an OpenAI-style response dict containing the full message.

        Raises:
            AdapterError: If OpenAI returns an error.
        """
        logger.info(f"[OpenAIAdapter] chat payload: model={self.model_name}, temp={temperature}, max_tokens={max_tokens}")
        try:
            response = await client.chat.completions.create(
                model=self.model_name,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
            )
        except OpenAIError as e:
            logger.error(f"[OpenAIAdapter] chat error: {e}")
            raise AdapterError("Upstream OpenAI chat failed", status_code=502)

        return {
            "id": response.id,
            "object": response.object,
            "model": response.model,
            "choices": [
                {
                    "role": response.choices[0].message.role,
                    "content": response.choices[0].message.content
                }
            ]
        }

    async def chat_stream(
        self,
        messages: List[Dict[str, str]],
        temperature: float | None = 0.7,
        max_tokens: int | None = 1024
    ) -> AsyncIterator[str]:
        """
        Perform a streaming chat completion using OpenAI SSE interface.

        Yields:
            str: JSON chunk for each message part.

        Raises:
            AdapterError: If OpenAI returns an error.
        """
        logger.info(f"[OpenAIAdapter] chat_stream payload: model={self.model_name}, temp={temperature}, max_tokens={max_tokens}")
        try:
            stream = await client.chat.completions.create(
                model=self.model_name,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
                stream=True,
            )
        except OpenAIError as e:
            logger.error(f"[OpenAIAdapter] chat_stream error: {e}")
            raise AdapterError("Upstream OpenAI streaming failed", status_code=502)

        async for chunk in stream:
            if chunk.choices:
                yield json.dumps({
                    "id": str(uuid.uuid4()),
                    "object": "chat.completion.chunk",
                    "model": self.model_name,
                    "choices": [chunk.choices[0].model_dump()],
                })

    async def embed(self, texts: List[str]) -> Dict[str, Any]:
        """
        Generate vector embeddings for a list of input texts.

        Returns:
            Dict[str, Any]: JSON-safe embedding result.

        Raises:
            AdapterError: If OpenAI returns an error.
        """
        logger.info(f"[OpenAIAdapter] embedding payload: model={self.model_name}, input_len={len(texts)}")
        try:
            response = await client.embeddings.create(
                model=self.model_name,
                input=texts,
            )
        except OpenAIError as e:
            logger.error(f"[OpenAIAdapter] embed error: {e}")
            raise AdapterError("Upstream OpenAI embedding failed", status_code=502)

        return {
            "object": "list",
            "data": [e.model_dump() for e in response.data],
            "model": self.model_name,
            "usage": response.usage.model_dump() if hasattr(response, "usage") else {}
        }


# ────── Adapter Export ──────
def get_adapter(model_name: str) -> BaseAdapter:
    """
    Factory method for loading the adapter from the router.
    """
    return OpenAIAdapter(model_name)
