"""Base chunking abstractions."""

from abc import ABC, abstractmethod
from typing import List

from app.data_layer.models import DocumentChunk, KnowledgeDocument


class BaseChunker(ABC):
    """Base class that centralizes chunk validation and object creation."""

    def __init__(self, chunk_size_tokens: int, chunk_overlap_tokens: int):
        if chunk_size_tokens <= 0:
            raise ValueError("chunk_size_tokens must be positive")
        if chunk_overlap_tokens < 0:
            raise ValueError("chunk_overlap_tokens cannot be negative")
        if chunk_overlap_tokens >= chunk_size_tokens:
            raise ValueError("chunk_overlap_tokens must be smaller than chunk_size_tokens")

        self.chunk_size_tokens = chunk_size_tokens
        self.chunk_overlap_tokens = chunk_overlap_tokens

    @abstractmethod
    def chunk(self, document: KnowledgeDocument) -> List[DocumentChunk]:
        """Split a normalized document into chunks."""

    def _make_chunk(self, document: KnowledgeDocument, index: int, text: str, token_count: int) -> DocumentChunk:
        return DocumentChunk(
            chunk_id="%s::chunk-%s" % (document.document_id, index),
            document_id=document.document_id,
            title=document.title,
            text=text,
            source_path=document.source_path,
            token_count=token_count,
            metadata=document.metadata,
        )
