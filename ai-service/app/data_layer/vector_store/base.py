"""Base vector-store abstractions."""

from abc import ABC, abstractmethod
from typing import Iterable, List

from app.data_layer.models import IndexedChunk, RetrievalResult


class BaseVectorStore(ABC):
    """Abstract base for vector database backends.

    Concrete stores are responsible for persistence and similarity search, while
    callers interact with this stable contract.
    """

    @abstractmethod
    def upsert(self, chunks: Iterable[IndexedChunk]) -> None:
        """Persist or replace indexed chunks in the backend."""

    @abstractmethod
    def load_chunks(self) -> List[IndexedChunk]:
        """Load indexed chunks or metadata needed by the backend."""

    @abstractmethod
    def search(self, query_embedding: List[float], top_k: int) -> List[RetrievalResult]:
        """Run similarity search for the provided query embedding."""
