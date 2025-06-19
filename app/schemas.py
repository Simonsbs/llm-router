# app/schemas.py

from pydantic import BaseModel, Field
from typing import List, Dict

class ChatRequest(BaseModel):
    messages: List[Dict[str, str]]
    temperature: float | None = 0.7
    max_tokens: int | None = 1024
    stream: bool | None = False

class EmbeddingRequest(BaseModel):
    input: List[str] = Field(
        ..., examples=[["What is Simon B. Stirling known for?"]]
    )
