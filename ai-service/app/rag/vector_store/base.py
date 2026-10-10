"""Base vector-store abstractions for the retrieval subsystem."""

from abc import ABC, abstractmethod
from typing import Iterable, List

from app.data_layer.models import IndexedChunk, RetrievalResult


class BaseVectorStore(ABC):
    """Stable contract for dense vector persistence and similarity search."""

    @abstractmethod
    def upsert(self, chunks: Iterable[IndexedChunk]) -> None:
        """Persist or replace indexed chunks in the backend."""

    @abstractmethod
    def load_chunks(self) -> List[IndexedChunk]:
        """Load indexed chunks or metadata required by the backend."""

    @abstractmethod
    def search(self, query_embedding: List[float], top_k: int) -> List[RetrievalResult]:
        """Run similarity search for the provided query embedding."""
