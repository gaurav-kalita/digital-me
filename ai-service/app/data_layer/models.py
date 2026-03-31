"""Core models for the offline RAG data pipeline.

The data layer is intentionally split into stage-specific models so that each
pipeline step has a clear contract:

- `KnowledgeDocument`: normalized source document
- `DocumentChunk`: chunked unit ready for indexing
- `IndexedChunk`: chunk with an embedding persisted in the offline index
- `RetrievalResult`: online search result returned to the RAG stack
"""

from dataclasses import dataclass, field
from typing import Dict, List


@dataclass(frozen=True)
class KnowledgeDocument:
    """Normalized source document produced by the loader/cleaner stages."""

    document_id: str
    title: str
    content: str
    source_path: str
    metadata: Dict[str, str] = field(default_factory=dict)


@dataclass(frozen=True)
class DocumentChunk:
    """Token-sized chunk produced by the chunking stage."""

    chunk_id: str
    document_id: str
    title: str
    text: str
    source_path: str
    token_count: int
    metadata: Dict[str, str] = field(default_factory=dict)


@dataclass(frozen=True)
class IndexedChunk:
    """Chunk with embedding data persisted by the offline indexing pipeline."""

    chunk_id: str
    document_id: str
    title: str
    text: str
    source_path: str
    token_count: int
    embedding: List[float]
    metadata: Dict[str, str] = field(default_factory=dict)


@dataclass(frozen=True)
class RetrievalResult:
    """Online retrieval candidate passed to reranking and context building."""

    chunk_id: str
    document_id: str
    title: str
    text: str
    source_path: str
    score: float
    token_count: int
    metadata: Dict[str, str] = field(default_factory=dict)

    def to_source_label(self) -> str:
        return self.title or self.source_path
