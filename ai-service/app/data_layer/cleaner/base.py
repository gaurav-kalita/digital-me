"""Base cleaner abstractions."""

from abc import ABC, abstractmethod


class BaseCleaner(ABC):
    """Contract for document cleaning strategies."""

    @abstractmethod
    def clean(self, text: str) -> str:
        """Normalize a raw text document without changing its meaning."""
