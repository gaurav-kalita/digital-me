"""Backward-compatible re-exports for offline data-layer ports."""

from app.core.ports.data_access import Chunker, DocumentLoader, Embedder, TextCleaner

__all__ = ["Chunker", "DocumentLoader", "Embedder", "TextCleaner"]
