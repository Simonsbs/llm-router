# app/adapters/runnables.py

"""
Defines `RunnableLambda` chains for supported LLM providers.

These lambdas wrap backend-specific adapter calls (OpenAI, Ollama, DeepSeek)
to allow unified interaction via LangChain's `Runnable` interface.

This enables composability and future extension via LangChain pipelines,
agent flows, or serverless chains.

🧠 Why use RunnableLambda?
- Abstract away provider details
- Enable plug-and-play routing by model name
- Eventually compose into LangChain agent flows, RAG pipelines, etc.
"""

import asyncio
from langchain_core.runnables import RunnableLambda

# Each provider exposes a `get_adapter(model_id) -> BaseAdapter` function
from .ollama_adapter import get_adapter as get_ollama
from .openai_adapter import get_adapter as get_openai
from .deepseek_adapter import get_adapter as get_deepseek  # 👈 NEW


# ─── Ollama Chain ─────────────────────────────────────────────────────────────
ollama_chain = RunnableLambda(
    lambda inputs: asyncio.run(
        get_ollama(inputs["model"]).chat(
            inputs["messages"], inputs["temperature"], inputs["max_tokens"]
        )
    )
)

# ─── OpenAI Chain ─────────────────────────────────────────────────────────────
openai_chain = RunnableLambda(
    lambda inputs: asyncio.run(
        get_openai(inputs["model"]).chat(
            inputs["messages"], inputs["temperature"], inputs["max_tokens"]
        )
    )
)

# ─── DeepSeek Chain ───────────────────────────────────────────────────────────
deepseek_chain = RunnableLambda(
    lambda inputs: asyncio.run(
        get_deepseek(inputs["model"]).chat(
            inputs["messages"], inputs["temperature"], inputs["max_tokens"]
        )
    )
)


# ─── Routing Logic ────────────────────────────────────────────────────────────
def _route(inputs: dict):
    """
    Route to the correct Runnable chain based on `model` prefix.
    
    Args:
        inputs (dict): Dictionary containing at minimum a `model` key.

    Returns:
        RunnableLambda: The appropriate LLM adapter chain to invoke.
    """
    model_id = inputs.get("model", "")
    provider = model_id.split(":", 1)[0] if ":" in model_id else "ollama"

    return {
        "ollama": ollama_chain,
        "openai": openai_chain,
        "deepseek": deepseek_chain,
    }.get(provider, ollama_chain)  # default to Ollama


# Exposed as a unified entry point
router_chain = RunnableLambda(_route)
