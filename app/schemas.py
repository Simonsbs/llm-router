# app/schemas.py

"""
Defines Pydantic data models for request validation in the SimonGPT API.

These models serve three primary purposes:
1. Ensure incoming requests conform to expected shapes and types
2. Provide automatic OpenAPI schema generation for FastAPI
3. Add business logic validation (e.g., max character limits)

These models are consumed by FastAPI endpoint functions and dependency resolvers.

💡 These schemas enforce security and performance boundaries (e.g., token limits)
at the API edge before anything hits an LLM backend.
"""

from typing import List, Dict
from pydantic import BaseModel, Field, model_validator
from app.config import settings


class ChatRequest(BaseModel):
    """
    Defines the expected schema for a /v1/chat/completions request.

    Fields:
        messages (List[Dict[str, str]]): Required chat history in OpenAI format
            e.g., [{"role": "user", "content": "Hello!"}, ...]
        temperature (float | None): Optional generation randomness
        max_tokens (int | None): Optional limit on response length
        stream (bool | None): Whether to use streaming responses (Server-Sent Events)
    """
    messages: List[Dict[str, str]]
    temperature: float | None = 0.7
    max_tokens: int | None = 1024
    stream: bool | None = False

    @model_validator(mode="after")
    def check_payload_limits(cls, model):
        """
        Enforces global constraints:
        - Total input message length must be under `max_input_chars`
        - `max_tokens` must be within bounds

        Raises:
            ValueError: If message length or max_tokens exceeds allowed thresholds.
        """
        # 1. Character count limit for all input messages
        total_chars = sum(len(m.get("content", "")) for m in model.messages)
        if total_chars > settings.max_input_chars:
            raise ValueError(
                f"Total message content too large ({total_chars} chars); "
                f"max is {settings.max_input_chars}"
            )

        # 2. Token count limit for generation
        if model.max_tokens and model.max_tokens > settings.max_model_tokens:
            raise ValueError(
                f"Requested max_tokens ({model.max_tokens}) exceeds limit "
                f"({settings.max_model_tokens})"
            )

        return model


class EmbeddingRequest(BaseModel):
    """
    Defines the expected schema for a /v1/embeddings request.

    Fields:
        input (List[str]): Required list of strings to embed.
    """
    input: List[str] = Field(
        ...,
        examples=[["What is Simon B. Stirling known for?"]],
        description="A list of strings to convert into embeddings."
    )
