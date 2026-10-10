"""Generation provider abstractions."""

from abc import ABC, abstractmethod


class BaseLLMProvider(ABC):
    """Stable contract for text generation providers."""

    @abstractmethod
    async def generate(self, prompt: str) -> str:
        """Generate a response for the provided prompt."""
