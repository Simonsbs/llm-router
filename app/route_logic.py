# app/route_logic.py

"""
This module contains the logic used to select the appropriate LLM adapter
and model based on the incoming request type and payload.

This is effectively the “router brain” for the SimonGPT LLM service.

🔁 Purpose:
- Given a request type (chat, stream_chat, embed), determine the correct LLM provider.
- Return the provider name and model identifier for the downstream adapter system.

This pattern supports modular growth — new logic can later be added for:
- per-user preferences
- A/B testing
- usage-based routing
- model auto-selection based on input size, features, latency, etc.
"""

from typing import Tuple, Dict, Any


def select_adapter_and_model(
    request_type: str,
    payload: Dict[str, Any]
) -> Tuple[str, str]:
    """
    Determine which provider adapter and model ID to use for a given request.

    Args:
        request_type (str): One of "chat", "stream_chat", "embed"
        payload (Dict[str, Any]): The incoming request body

    Returns:
        Tuple[str, str]: A tuple of (provider_name, model_id)
                         e.g., ("openai", "openai:gpt-3.5-turbo-0125")

    Notes:
    - Current implementation is hardcoded to OpenAI for all routes.
    - You can later extend this to support model switching, preferences, etc.
    """

    # ─── Chat request (non-streaming) ──────────────────────────────────────────
    if request_type == "chat":
        return "openai", "openai:gpt-3.5-turbo-0125"

    # ─── Chat request (streaming) ──────────────────────────────────────────────
    elif request_type == "stream_chat":
        return "openai", "openai:gpt-3.5-turbo-0125"

    # ─── Embedding request ─────────────────────────────────────────────────────
    elif request_type == "embed":
        return "openai", "openai:text-embedding-3-small"

    # ─── Fallback ──────────────────────────────────────────────────────────────
    return "openai", "openai:gpt-3.5-turbo-0125"
