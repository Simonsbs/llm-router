import asyncio
from langchain_core.runnables import RunnableLambda
from .ollama_adapter import get_adapter as get_ollama
from .openai_adapter import get_adapter as get_openai
from .deepseek_adapter import get_adapter as get_deepseek  # 👈 NEW

ollama_chain = RunnableLambda(
    lambda inputs: asyncio.run(
        get_ollama(inputs["model"]).chat(
            inputs["messages"], inputs["temperature"], inputs["max_tokens"]
        )
    )
)

openai_chain = RunnableLambda(
    lambda inputs: asyncio.run(
        get_openai(inputs["model"]).chat(
            inputs["messages"], inputs["temperature"], inputs["max_tokens"]
        )
    )
)

deepseek_chain = RunnableLambda(  # 👈 NEW
    lambda inputs: asyncio.run(
        get_deepseek(inputs["model"]).chat(
            inputs["messages"], inputs["temperature"], inputs["max_tokens"]
        )
    )
)

def _route(inputs: dict):
    model_id = inputs.get("model", "")
    provider = model_id.split(":", 1)[0] if ":" in model_id else "ollama"
    return {
        "ollama": ollama_chain,
        "openai": openai_chain,
        "deepseek": deepseek_chain,
    }.get(provider, ollama_chain)

router_chain = RunnableLambda(_route)
