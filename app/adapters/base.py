# app/adapters/base.py

"""
Defines the `BaseAdapter` abstract class — a contract for all LLM provider adapters.

Every provider adapter (e.g., OpenAI, Ollama, DeepSeek) must implement this interface.
It defines a consistent set of async methods to:
- Perform synchronous completions (`chat`)
- Perform streaming completions (`chat_stream`)
- Generate embeddings (`embed`)

🔁 Why use this abstraction?
- Enables polymorphic routing across providers
- Forces consistency across adapter implementations
- Makes it easy to plug new providers into the system

Each adapter should implement logic in a fault-tolerant, token-conscious way.
"""

from abc import ABC, abstractmethod
from typing import Dict, List, Any, AsyncIterator


class BaseAdapter(ABC):
    """
    Abstract base class for all provider adapters.

    Each adapter wraps a specific LLM API (e.g., OpenAI, Ollama) and
    exposes a consistent interface for FastAPI to use.
    """

    def __init__(self, model_name: str) -> None:
        """
        Args:
            model_name (str): Full model ID including provider prefix (e.g. "openai:gpt-4.1").
        """
        self.model_name = model_name

    @abstractmethod
    async def chat(
        self,
        messages: List[Dict[str, str]],
        temperature: float | None,
        max_tokens: int | None,
    ) -> Any:
        """
        Send a non-streaming chat request to the provider.

        Args:
            messages (List[Dict]): Chat history in OpenAI-style format.
            temperature (float): Sampling randomness.
            max_tokens (int): Max output length in tokens.

        Returns:
            Provider-specific response object or dict.
        """
        ...

    @abstractmethod
    async def chat_stream(
        self,
        messages: List[Dict[str, str]],
        temperature: float | None,
        max_tokens: int | None,
    ) -> AsyncIterator[str]:
        """
        Stream response chunks from the provider (SSE-style).

        Args:
            messages (List[Dict]): Chat history.
            temperature (float): Sampling temperature.
            max_tokens (int): Max response tokens.

        Yields:
            str: Chunks of text.
        """
        ...

    @abstractmethod
    async def embed(
        self,
        texts: List[str]
    ) -> Dict[str, Any]:
        """
        Generate vector embeddings for a list of strings.

        Args:
            texts (List[str]): Sentences or documents to embed.

        Returns:
            Dict[str, Any]: Provider-specific embedding response.
        """
        ...
