# app/adapters/adapter.py
import importlib
from typing import List, Dict, Any, AsyncIterator
from app.route_logic import select_adapter_and_model

class Adapter:
    def __init__(self, request_type: str, payload: Dict[str, Any]):
        self.request_type = request_type
        self.payload = payload
        provider, model_id = select_adapter_and_model(request_type, payload)
        module = importlib.import_module(f"app.adapters.{provider}_adapter")
        self._inner = module.get_adapter(model_id)

    async def chat(
        self,
        messages: List[Dict[str, str]],
        temperature: float | None,
        max_tokens: int | None
    ) -> Any:
        return await self._inner.chat(messages, temperature, max_tokens)

    async def chat_stream(
        self,
        messages: List[Dict[str, str]],
        temperature: float | None,
        max_tokens: int | None
    ) -> AsyncIterator[str]:
        async for chunk in self._inner.chat_stream(messages, temperature, max_tokens):
            yield chunk

    async def embed(self, inputs: List[str]) -> Any:
        return await self._inner.embed(inputs)
