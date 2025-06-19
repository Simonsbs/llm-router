# app/config.py
from pydantic_settings import BaseSettings
from pydantic import ConfigDict, Extra, field_validator, AnyHttpUrl, Field
from typing import List, Union, Literal

class Settings(BaseSettings):
    # ─── Secrets (must come from env/.env) ───────────────────────────────────────
    llm_router_api_key: str
    jwt_secret_key: str

    # ─── LLM Endpoints ─────────────────────────────────────────────────────────
    # OpenAI base URL is almost always https://api.openai.com
    openai_api_base: AnyHttpUrl = "https://api.openai.com"
    # Ollama default in-Docker address; override via OLLAMA_URL if needed
    ollama_url: AnyHttpUrl = Field(
        default="http://host.docker.internal:11434",
        env="OLLAMA_URL"
    )

    # ─── CORS ────────────────────────────────────────────────────────────────────
    # allow either literal "*" or a list of real URLs
    cors_origins: List[Union[AnyHttpUrl, Literal["*"]]] = ["*"]

    # ─── Rate limits ────────────────────────────────────────────────────────────
    rate_limit_token: str = "10/minute"
    rate_limit_chat:  str = "30/minute"
    rate_limit_embed: str = "60/minute"

    # ─── Model defaults (for route logic) ───────────────────────────────────────
    default_chat_model: str = "openai:gpt-3.5-turbo-0125"
    default_embed_model: str = "openai:text-embedding-3-small"

    # ─── Pydantic config ────────────────────────────────────────────────────────
    model_config = ConfigDict(
        env_file = ".env",
        env_file_encoding = "utf-8",
        extra = Extra.ignore,    # ignore other envs like OPENAI_API_KEY, etc.
    )

    # ─── Validators ─────────────────────────────────────────────────────────────
    @field_validator("rate_limit_token", "rate_limit_chat", "rate_limit_embed")
    @classmethod
    def check_rate_limit_format(cls, v: str) -> str:
        if "/" not in v:
            raise ValueError("rate limits must be of form `<num>/<unit>`, e.g. `30/minute`")
        return v

settings = Settings()
