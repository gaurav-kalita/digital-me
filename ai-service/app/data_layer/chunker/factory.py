"""Chunker factory and selection policy."""

from typing import Optional

from app.core.config import settings
from app.core.logger import logger
from app.data_layer.chunker.base import BaseChunker
from app.data_layer.chunker.huggingface import HuggingFaceChunker
from app.data_layer.chunker.tiktoken_chunker import TiktokenChunker
from app.data_layer.chunker.word import WordTokenChunker


class ChunkerFactory:
    """Factory for selecting a chunker implementation from configuration."""

    @staticmethod
    def create(
        chunker_type: Optional[str] = None,
        chunk_size_tokens: Optional[int] = None,
        chunk_overlap_tokens: Optional[int] = None,
        encoding_name: Optional[str] = None,
        encoding=None,
        tokenizer=None,
        model_name: Optional[str] = None,
    ) -> BaseChunker:
        selected_type = (chunker_type or settings.chunking.strategy).lower()
        size = chunk_size_tokens or settings.chunking.chunk_size_tokens
        overlap = chunk_overlap_tokens if chunk_overlap_tokens is not None else settings.chunking.chunk_overlap_tokens

        if selected_type in {"word", "word_token", "basic"}:
            return WordTokenChunker(chunk_size_tokens=size, chunk_overlap_tokens=overlap)

        if selected_type in {"tiktoken", "tokenizer"}:
            try:
                return TiktokenChunker(
                    chunk_size_tokens=size,
                    chunk_overlap_tokens=overlap,
                    encoding_name=encoding_name or settings.chunking.encoding_name,
                    encoding=encoding,
                )
            except Exception:
                logger.warning(
                    "Falling back to WordTokenChunker because tokenizer-backed chunker could not be initialized",
                    exc_info=True,
                )
                return WordTokenChunker(chunk_size_tokens=size, chunk_overlap_tokens=overlap)

        if selected_type in {"huggingface", "hf", "transformers"}:
            try:
                return HuggingFaceChunker(
                    chunk_size_tokens=size,
                    chunk_overlap_tokens=overlap,
                    model_name=model_name or settings.chunking.huggingface_model_name,
                    tokenizer=tokenizer,
                )
            except Exception:
                logger.warning(
                    "Falling back to WordTokenChunker because HuggingFace tokenizer failed",
                    exc_info=True,
                )
                return WordTokenChunker(chunk_size_tokens=size, chunk_overlap_tokens=overlap)

        raise ValueError("Unsupported chunker type: %s" % selected_type)
