from abc import ABC, abstractmethod
from typing import Dict, List, Any, AsyncIterator

class BaseAdapter(ABC):
    """All providers implement chat, chat_stream, and embeddings."""

    def __init__(self, model_name: str) -> None:
        self.model_name = model_name

    @abstractmethod
    async def chat(
        self,
        messages: List[Dict[str, str]],
        temperature: float | None,
        max_tokens: int | None,
    ) -> Any: ...

    @abstractmethod
    async def chat_stream(
        self,
        messages: List[Dict[str, str]],
        temperature: float | None,
        max_tokens: int | None,
    ) -> AsyncIterator[str]: ...

    @abstractmethod
    async def embed(
        self,
        texts: List[str]
    ) -> Dict[str, Any]: ...
