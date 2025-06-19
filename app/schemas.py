# app/schemas.py

from pydantic import BaseModel, Field
from typing import List, Dict
from app.config import settings
from pydantic import BaseModel, Field, model_validator


class ChatRequest(BaseModel):
    messages: List[Dict[str, str]]
    temperature: float | None = 0.7
    max_tokens: int | None = 1024
    stream: bool | None = False

    @model_validator(mode="after")
    def check_payload_limits(cls, model):
        # 1) Total content length
        total_chars = sum(len(m.get("content", "")) for m in model.messages)
        if total_chars > settings.max_input_chars:
           raise ValueError(
               f"Total message content too large ({total_chars} chars); max is {settings.max_input_chars}"
           )
        # 2) max_tokens cap
        if model.max_tokens and model.max_tokens > settings.max_model_tokens:
           raise ValueError(
               f"Requested max_tokens ({model.max_tokens}) exceeds limit ({settings.max_model_tokens})"
           )
        return model

class EmbeddingRequest(BaseModel):
    input: List[str] = Field(
        ..., examples=[["What is Simon B. Stirling known for?"]]
    )
