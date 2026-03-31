"""Tokenizer-backed chunker using Hugging Face tokenizers."""

from typing import List

from app.data_layer.chunker.base import BaseChunker
from app.data_layer.models import DocumentChunk, KnowledgeDocument


class HuggingFaceChunker(BaseChunker):
    """Chunker powered by a Hugging Face tokenizer."""

    def __init__(
        self,
        chunk_size_tokens: int = 240,
        chunk_overlap_tokens: int = 40,
        model_name: str = "bert-base-uncased",
        tokenizer=None,
    ):
        super().__init__(chunk_size_tokens=chunk_size_tokens, chunk_overlap_tokens=chunk_overlap_tokens)
        self.model_name = model_name
        self._tokenizer = tokenizer or self._load_tokenizer(model_name)

    def chunk(self, document: KnowledgeDocument) -> List[DocumentChunk]:
        token_ids = self._tokenizer.encode(document.content, add_special_tokens=False)
        if not token_ids:
            return []

        chunks: List[DocumentChunk] = []
        step = max(self.chunk_size_tokens - self.chunk_overlap_tokens, 1)

        for index, start in enumerate(range(0, len(token_ids), step)):
            end = min(start + self.chunk_size_tokens, len(token_ids))
            chunk_token_ids = token_ids[start:end]
            if not chunk_token_ids:
                continue

            chunk_text = self._tokenizer.decode(chunk_token_ids, skip_special_tokens=True).strip()
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

    def _load_tokenizer(self, model_name: str):
        try:
            from transformers import AutoTokenizer
        except ImportError as exc:
            raise RuntimeError("transformers is required for the HuggingFace chunker") from exc

        try:
            return AutoTokenizer.from_pretrained(model_name, local_files_only=True)
        except Exception as exc:
            raise RuntimeError("Failed to load Hugging Face tokenizer: %s" % model_name) from exc
