# app/config.py

"""
Configuration module for the SimonGPT LLM Router service.

This module defines the application's runtime configuration using Pydantic's `BaseSettings` class,
allowing environment variable management, validation, and default values.

Environment variables are loaded from a `.env` file or system environment.
All settings in this file are validated and can be type-checked at runtime.

This config powers:
- Rate limits
- API endpoint routing
- Secret keys
- CORS policies
- Model selection defaults

🔐 Ensure `.env` is provided with valid secrets and keys in deployment.
"""

from pydantic_settings import BaseSettings
from pydantic import ConfigDict, Extra, field_validator, AnyHttpUrl, Field
from typing import List, Union, Literal


class Settings(BaseSettings):
    # ─── Secrets (required from .env or environment) ───────────────────────────
    llm_router_api_key: str  # Used to authenticate clients for issuing JWTs
    jwt_secret_key: str      # Secret key used to sign JWTs

    # ─── Model Limits ──────────────────────────────────────────────────────────
    max_input_chars: int = 16000  # Max total character count allowed in chat messages
    max_model_tokens: int = 4096  # Max model token generation capacity per request

    # ─── LLM Endpoint URLs ─────────────────────────────────────────────────────
    # OpenAI-compatible URL (default OpenAI endpoint)
    openai_api_base: AnyHttpUrl = "https://api.openai.com"

    # Ollama local API endpoint (commonly used for local model serving in Docker)
    ollama_url: AnyHttpUrl = Field(
        default="http://host.docker.internal:11434",
        env="OLLAMA_URL"  # allows override from environment
    )

    # ─── CORS Configuration ────────────────────────────────────────────────────
    # Allow list of origins for browser requests, use "*" to allow any origin
    cors_origins: List[Union[AnyHttpUrl, Literal["*"]]] = ["*"]

    # ─── Rate Limiting Policies ────────────────────────────────────────────────
    # Format must be "<count>/<unit>", e.g. "10/minute"
    rate_limit_token: str = "10/minute"   # Token exchange endpoint rate limit
    rate_limit_chat: str  = "30/minute"   # Chat completion endpoint limit
    rate_limit_embed: str = "60/minute"   # Embedding request limit

    # ─── Default Models ────────────────────────────────────────────────────────
    default_chat_model: str = "openai:gpt-3.5-turbo-0125"     # Used if no model is specified
    default_embed_model: str = "openai:text-embedding-3-small"  # Used for /v1/embedding requests

    # ─── Pydantic Global Configuration ─────────────────────────────────────────
    model_config = ConfigDict(
        env_file=".env",                     # Load settings from .env file
        env_file_encoding="utf-8",
        extra=Extra.ignore,                  # Ignore unknown env vars like OPENAI_API_KEY
    )

    # ─── Validators ────────────────────────────────────────────────────────────
    @field_validator("rate_limit_token", "rate_limit_chat", "rate_limit_embed")
    @classmethod
    def check_rate_limit_format(cls, v: str) -> str:
        """
        Validates rate limit string format: must include a "/" (e.g., "30/minute").
        This avoids malformed rate-limit strings that would break SlowAPI.
        """
        if "/" not in v:
            raise ValueError("rate limits must be of form `<num>/<unit>`, e.g. `30/minute`")
        return v


# Instantiate a singleton config object, importable throughout the app
settings = Settings()
