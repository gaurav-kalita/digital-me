"""Base embedder abstractions."""

from abc import ABC, abstractmethod
from typing import List


class BaseEmbedder(ABC):
    """Contract for vector embedders."""

    @abstractmethod
    def embed(self, text: str) -> List[float]:
        """Encode text into a dense vector."""
