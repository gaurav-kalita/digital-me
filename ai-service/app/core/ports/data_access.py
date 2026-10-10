"""Port definitions for offline ingestion and vector persistence."""

from typing import Iterable, List, Protocol, Tuple

from app.data_layer.models import DocumentChunk, IndexedChunk, KnowledgeDocument, RetrievalResult


class DocumentLoader(Protocol):
    """Loads source documents for offline ingestion."""

    def load(self) -> List[KnowledgeDocument]:
        ...


class TextCleaner(Protocol):
    """Normalizes raw source text before chunking."""

    def clean(self, text: str) -> str:
        ...


class Chunker(Protocol):
    """Splits normalized documents into token-aware chunks."""

    def chunk(self, document: KnowledgeDocument) -> List[DocumentChunk]:
        ...


class Embedder(Protocol):
    """Produces dense vector representations."""

    def embed(self, text: str) -> List[float]:
        ...


class ArtifactStore(Protocol):
    """Persists human-readable indexing artifacts."""

    def save(self, chunks: Iterable[IndexedChunk]) -> None:
        ...

    def load(self) -> List[IndexedChunk]:
        ...


class VectorStore(Protocol):
    """Persists vectors and serves similarity search results."""

    def upsert(self, chunks: Iterable[IndexedChunk]) -> None:
        ...

    def load_chunks(self) -> List[IndexedChunk]:
        ...

    def search(self, query_embedding: List[float], top_k: int) -> List[RetrievalResult]:
        ...
