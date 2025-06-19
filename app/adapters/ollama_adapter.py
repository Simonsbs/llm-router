import os, httpx, uuid, json, logging
from typing import List, Dict, Any, AsyncIterator
from .base import BaseAdapter

logger = logging.getLogger("app.adapters.ollama_adapter")

OLLAMA_URL = os.getenv("OLLAMA_URL", "http://host.docker.internal:11434")

class OllamaAdapter(BaseAdapter):
    def __init__(self, model_name: str):
        self.model_name = model_name

    async def embed(self, inputs: list[str]) -> dict:
        url = f"{OLLAMA_URL}/api/embed"
        payload = {"model": self.model_name, "input": inputs}
        logger.info(f"[OllamaAdapter] embed payload: {payload}")

        async with httpx.AsyncClient(timeout=httpx.Timeout(60.0)) as client:
            response = await client.post(url, json=payload)
            logger.info(f"[OllamaAdapter] embed response status: {response.status_code}")
            response.raise_for_status()
            data = response.json()
            logger.info(f"[OllamaAdapter] embed raw response: {data}")
            return data

    async def chat(self, messages: List[Dict[str, str]], temperature: float | None, max_tokens: int | None) -> Dict[str, Any]:
        payload = {
            "model": self.model_name,
            "messages": messages,
            "stream": False,
            "options": {"temperature": temperature, "num_predict": max_tokens},
        }
        logger.info(f"[OllamaAdapter] chat payload: {payload}")
        async with httpx.AsyncClient(timeout=httpx.Timeout(60.0)) as client:
            resp = await client.post(f"{OLLAMA_URL}/api/chat", json=payload)
            logger.info(f"[OllamaAdapter] chat response status: {resp.status_code}")
            resp.raise_for_status()
            data = resp.json()
            logger.info(f"[OllamaAdapter] chat response data: {data}")

        return {
            "id": data.get("id", str(uuid.uuid4())),
            "object": "chat.completion",
            "model": self.model_name,
            "choices": [
                {
                    "role": data["message"].get("role", "assistant"),
                    "content": data["message"]["content"]
                }
            ]
        }

    async def chat_stream(self, messages: List[Dict[str, str]], temperature: float | None, max_tokens: int | None) -> AsyncIterator[str]:
        payload = {
            "model": self.model_name,
            "messages": messages,
            "stream": True,
            "options": {"temperature": temperature, "num_predict": max_tokens},
        }
        logger.info(f"[OllamaAdapter] chat_stream payload: {payload}")
        async with httpx.AsyncClient(timeout=httpx.Timeout(60.0)) as client:
            async with client.stream("POST", f"{OLLAMA_URL}/api/chat", json=payload) as resp:
                logger.info(f"[OllamaAdapter] chat_stream response status: {resp.status_code}")
                async for line in resp.aiter_lines():
                    if not line:
                        continue
                    chunk = json.loads(line)
                    logger.info(f"[OllamaAdapter] chat_stream chunk: {chunk}")
                    yield json.dumps(
                        {
                            "id": chunk.get("id", str(uuid.uuid4())),
                            "object": "chat.completion.chunk",
                            "model": self.model_name,
                            "choices": [
                                {
                                    "role": chunk["message"].get("role", "assistant"),
                                    "content": chunk["message"]["content"]
                                }
                            ],
                        }
                    )

def get_adapter(model_name: str) -> BaseAdapter:
    return OllamaAdapter(model_name)
