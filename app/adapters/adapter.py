# app/adapters/adapter.py

"""
Defines the dynamic adapter loader and request router.

This class serves as the runtime glue between:
- The incoming request (chat, stream_chat, embed)
- The model routing logic (via route_logic.py)
- The provider-specific adapter module (e.g., openai_adapter)

🧠 Purpose:
- Dynamically determine the provider + model for each request
- Import the appropriate adapter at runtime
- Delegate method calls (`chat`, `chat_stream`, `embed`) to the inner adapter

This allows the service to support multiple providers without hardcoding any one.
"""

import importlib
from typing import List, Dict, Any, AsyncIterator

from app.route_logic import select_adapter_and_model


class Adapter:
    """
    Unified adapter entry point for a single request.

    Based on the request type and payload, it:
    - Selects the appropriate provider + model
    - Loads the matching adapter module (e.g. OpenAI)
    - Delegates all method calls to that adapter
    """

    def __init__(self, request_type: str, payload: Dict[str, Any]):
        """
        Args:
            request_type (str): One of "chat", "stream_chat", or "embed"
            payload (Dict[str, Any]): The validated FastAPI request body
        """
        self.request_type = request_type
        self.payload = payload

        # Dynamically choose provider + model
        provider, model_id = select_adapter_and_model(request_type, payload)

        # Dynamically import the matching adapter module
        module = importlib.import_module(f"app.adapters.{provider}_adapter")
        self._inner = module.get_adapter(model_id)

    async def chat(
        self,
        messages: List[Dict[str, str]],
        temperature: float | None,
        max_tokens: int | None
    ) -> Any:
        """
        Non-streaming completion request to inner adapter.
        """
        return await self._inner.chat(messages, temperature, max_tokens)

    async def chat_stream(
        self,
        messages: List[Dict[str, str]],
        temperature: float | None,
        max_tokens: int | None
    ) -> AsyncIterator[str]:
        """
        Streaming response generator (SSE-compatible).
        """
        async for chunk in self._inner.chat_stream(messages, temperature, max_tokens):
            yield chunk

    async def embed(self, inputs: List[str]) -> Any:
        """
        Embedding request to inner adapter.
        """
        return await self._inner.embed(inputs)
