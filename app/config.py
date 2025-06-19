# app/config.py

from pydantic_settings import BaseSettings
from typing import List
from pydantic import ConfigDict, Extra

class Settings(BaseSettings):
    # Secrets
    llm_router_api_key: str
    jwt_secret_key: str

    # CORS: wildcard or specific origins
    cors_origins: List[str] = ["*"]

    # Rate-limits
    rate_limit_token: str = "10/minute"
    rate_limit_chat:  str = "30/minute"
    rate_limit_embed: str = "60/minute"

    # Adapter defaults (for future route_logic)
    default_chat_model: str = "openai:gpt-3.5-turbo-0125"
    default_embed_model: str = "openai:text-embedding-3-small"

    # Validation limits
    max_input_chars: int = 15000    # total characters across all messages
    max_model_tokens: int = 2048    # maximum tokens allowed by the model

    model_config = ConfigDict(
        env_file = ".env",
        env_file_encoding = "utf-8",
        extra = Extra.ignore,    # ignore DEEPSEEK_API_KEY, OPENAI_API_KEY, etc.
    )

# instantiate once for import
settings = Settings()
