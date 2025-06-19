import os, uuid, json, logging
from typing import List, Dict, Any, AsyncIterator
from openai import AsyncOpenAI, OpenAIError
from .base import BaseAdapter
from app.exceptions import AdapterError


logger = logging.getLogger("app.adapters.openai_adapter")

client = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))

class OpenAIAdapter(BaseAdapter):
    def __init__(self, model_name: str):
        # Strip provider prefix if present (e.g., "openai:gpt-4o" -> "gpt-4o")
        self.model_name = model_name.split(":", 1)[1] if ":" in model_name else model_name

    async def chat(self, messages: List[Dict[str, str]], temperature: float | None = 0.7, max_tokens: int | None = 1024) -> Dict[str, Any]:
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
            raise AdapterError(
                detail="Upstream OpenAI chat failed",
                status_code=502
            )

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

    async def chat_stream(self, messages: List[Dict[str, str]], temperature: float | None = 0.7, max_tokens: int | None = 1024) -> AsyncIterator[str]:
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
            raise AdapterError(
                detail="Upstream OpenAI streaming failed",
                status_code=502
            )
        async for chunk in stream:
            if chunk.choices:
                yield json.dumps({
                    "id": str(uuid.uuid4()),
                    "object": "chat.completion.chunk",
                    "model": self.model_name,
                    "choices": [chunk.choices[0].model_dump()],
                })

    async def embed(self, texts: List[str]) -> Dict[str, Any]:
        logger.info(f"[OpenAIAdapter] embedding payload: model={self.model_name}, input_len={len(texts)}")
        try:
            response = await client.embeddings.create(
                model=self.model_name,
                input=texts,
            )
        except OpenAIError as e:
            logger.error(f"[OpenAIAdapter] embed error: {e}")
            raise AdapterError(
                detail="Upstream OpenAI embedding failed",
                status_code=502
            )   
        return {
            "object": "list",
            "data": [e.model_dump() for e in response.data],
            "model": self.model_name,
            "usage": response.usage.model_dump() if hasattr(response, "usage") else {}
        }

def get_adapter(model_name: str) -> BaseAdapter:
    return OpenAIAdapter(model_name)