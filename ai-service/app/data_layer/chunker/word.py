"""Whitespace-token chunking strategy."""

from typing import List

from app.data_layer.chunker.base import BaseChunker
from app.data_layer.models import DocumentChunk, KnowledgeDocument


class WordTokenChunker(BaseChunker):
    """Low-overhead whitespace-token chunker used as a stable fallback."""

    def chunk(self, document: KnowledgeDocument) -> List[DocumentChunk]:
        tokens = document.content.split()
        if not tokens:
            return []

        chunks: List[DocumentChunk] = []
        step = max(self.chunk_size_tokens - self.chunk_overlap_tokens, 1)

        for index, start in enumerate(range(0, len(tokens), step)):
            end = min(start + self.chunk_size_tokens, len(tokens))
            chunk_tokens = tokens[start:end]
            if not chunk_tokens:
                continue

            chunks.append(
                self._make_chunk(
                    document=document,
                    index=index,
                    text=" ".join(chunk_tokens),
                    token_count=len(chunk_tokens),
                )
            )

            if end >= len(tokens):
                break

        return chunks
