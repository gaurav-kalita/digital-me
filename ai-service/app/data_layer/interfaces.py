"""Protocols for pluggable offline/online data-layer components."""

from typing import Iterable, List, Protocol

from app.data_layer.models import DocumentChunk, IndexedChunk, KnowledgeDocument, RetrievalResult


class DocumentLoader(Protocol):
    def load(self) -> List[KnowledgeDocument]:
        ...


class TextCleaner(Protocol):
    def clean(self, text: str) -> str:
        ...


class Chunker(Protocol):
    def chunk(self, document: KnowledgeDocument) -> List[DocumentChunk]:
        ...


class Embedder(Protocol):
    def embed(self, text: str) -> List[float]:
        ...


class VectorStore(Protocol):
    """Database boundary for storing and querying embedded chunks."""

    def upsert(self, chunks: Iterable[IndexedChunk]) -> None:
        ...

    def load_chunks(self) -> List[IndexedChunk]:
        ...

    def search(self, query_embedding: List[float], top_k: int) -> List[RetrievalResult]:
        ...
