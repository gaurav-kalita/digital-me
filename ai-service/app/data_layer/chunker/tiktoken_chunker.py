"""Tokenizer-backed chunker using tiktoken."""

from typing import List

from app.data_layer.chunker.base import BaseChunker
from app.data_layer.models import DocumentChunk, KnowledgeDocument


class TiktokenChunker(BaseChunker):
    """Tokenizer-backed chunker aligned with modern LLM token budgets."""

    def __init__(
        self,
        chunk_size_tokens: int = 240,
        chunk_overlap_tokens: int = 40,
        encoding_name: str = "cl100k_base",
        encoding=None,
    ):
        super().__init__(chunk_size_tokens=chunk_size_tokens, chunk_overlap_tokens=chunk_overlap_tokens)
        self.encoding_name = encoding_name
        self._encoding = encoding or self._load_encoding(encoding_name)

    def chunk(self, document: KnowledgeDocument) -> List[DocumentChunk]:
        token_ids = self._encoding.encode(document.content)
        if not token_ids:
            return []

        chunks: List[DocumentChunk] = []
        step = max(self.chunk_size_tokens - self.chunk_overlap_tokens, 1)

        for index, start in enumerate(range(0, len(token_ids), step)):
            end = min(start + self.chunk_size_tokens, len(token_ids))
            chunk_token_ids = token_ids[start:end]
            if not chunk_token_ids:
                continue

            chunk_text = self._encoding.decode(chunk_token_ids).strip()
            if not chunk_text:
                continue

            chunks.append(
                self._make_chunk(
                    document=document,
                    index=index,
                    text=chunk_text,
                    token_count=len(chunk_token_ids),
                )
            )

            if end >= len(token_ids):
                break

        return chunks

    def _load_encoding(self, encoding_name: str):
        try:
            import tiktoken
        except ImportError as exc:
            raise RuntimeError("tiktoken is required for the tiktoken chunker") from exc
        return tiktoken.get_encoding(encoding_name)
