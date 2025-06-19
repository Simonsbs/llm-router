# app/route_logic.py
from typing import Tuple, Dict, Any

def select_adapter_and_model(
    request_type: str,
    payload: Dict[str, Any]
) -> Tuple[str, str]:
    """
    Determine which provider adapter and model to use.
    Returns (provider_name, model_id).
    """
    # — Example logic: always OpenAI for now —
    if request_type == "chat":
        #return "openai", "openai:gpt-4.1-nano"
        return "openai", "openai:gpt-3.5-turbo-0125"
    elif request_type == "stream_chat":
        #return "openai", "openai:gpt-4.1-nano"
        return "openai", "openai:gpt-3.5-turbo-0125"
    elif request_type == "embed":
        return "openai", "openai:text-embedding-3-small"
    # fallback:
    return "openai", "openai:gpt-3.5-turbo-0125"
