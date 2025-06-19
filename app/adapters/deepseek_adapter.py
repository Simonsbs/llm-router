import os
import httpx
import logging
from typing import List, Dict, Any

logger = logging.getLogger("app.adapters.deepseek_adapter")

DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY")

CHAT_URL = "https://api.deepseek.com/v1/chat/completions"
EMBEDDING_URL = "https://api.deepseek.com/v1/embeddings"


class DeepSeekAdapter:
    def __init__(self, model_name: str):
        self.model_name = model_name.split(":")[-1]

    async def chat(
        self,
        messages: List[Dict[str, str]],
        temperature: float | None = 0.7,
        max_tokens: int | None = 1024,
    ) -> str:
        payload = {
            "model": self.model_name,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }

        headers = {
            "Authorization": f"Bearer {DEEPSEEK_API_KEY}",
            "Content-Type": "application/json",
        }

        logger.info(f"[DeepSeekAdapter] chat payload: {payload}")

        async with httpx.AsyncClient() as client:
            resp = await client.post(CHAT_URL, json=payload, headers=headers)
            logger.info(f"[DeepSeekAdapter] response status: {resp.status_code}")
            try:
                resp.raise_for_status()
            except httpx.HTTPStatusError:
                logger.error(f"DeepSeek chat error: {resp.text}")
                raise

            data = resp.json()
            return data["choices"][0]["message"]["content"]

    async def embed(self, text: str) -> List[float]:
        payload = {
            "model": self.model_name,
            "input": text,
        }

        headers = {
            "Authorization": f"Bearer {DEEPSEEK_API_KEY}",
            "Content-Type": "application/json",
        }

        logger.info(f"[DeepSeekAdapter] embedding payload: {payload}")

        async with httpx.AsyncClient() as client:
            resp = await client.post(EMBEDDING_URL, json=payload, headers=headers)
            logger.info(f"[DeepSeekAdapter] embed response status: {resp.status_code}")
            try:
                resp.raise_for_status()
            except httpx.HTTPStatusError:
                logger.error(f"DeepSeek embed error: {resp.text}")
                raise

            data = resp.json()
            return data["data"][0]["embedding"]


def get_adapter(model_name: str):
    return DeepSeekAdapter(model_name)
