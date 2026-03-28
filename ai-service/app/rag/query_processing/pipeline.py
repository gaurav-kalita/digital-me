# pipeline.py

from typing import Any, Dict, Optional


class QueryProcessingPipeline:
    def __init__(
        self,
        normalizer,
        rewriter,
        embedder,
        metadata_extractor,
        config: Optional[Dict[str, Any]] = None,
        logger=None,
    ):
        self.normalizer = normalizer
        self.rewriter = rewriter
        self.embedder = embedder
        self.metadata_extractor = metadata_extractor

        self.config = config or {}
        self.logger = logger

    def process(self, query: str, context: str = None) -> Dict[str, Any]:
        self._validate_input(query)

        # Step 1: Normalize
        normalized = self._safe_normalize(query)

        # Step 2: Rewrite (LLM)
        rewritten = self._safe_rewrite(normalized, context)

        # Step 3: Metadata Extraction
        metadata = self._safe_metadata_extract(rewritten)

        # Step 4: Embedding
        embedding = self._safe_embed(rewritten)

        return {
            "original_query": query,
            "normalized_query": normalized,
            "rewritten_query": rewritten,
            "embedding": embedding,
            "metadata": metadata,
        }

    # --------------------------
    # Validation
    # --------------------------
    def _validate_input(self, query: str):
        if not isinstance(query, str):
            raise TypeError("Query must be a string")

        if not query or len(query.strip()) < 3:
            raise ValueError("Query too short or empty")

        max_len = self.config.get("max_query_length", 512)
        if len(query) > max_len:
            raise ValueError(f"Query exceeds max length of {max_len}")

    # --------------------------
    # Safe Wrappers
    # --------------------------

    def _safe_normalize(self, query: str) -> str:
        try:
            return self.normalizer.normalize(query)
        except Exception as e:
            self._log_error("Normalization failed", e)
            return query  # fallback

    def _safe_rewrite(self, query: str, context: Optional[str]) -> str:
        try:
            return self.rewriter.rewrite(query, context)
        except Exception as e:
            self._log_error("Rewrite failed", e)
            return query  # fallback

    def _safe_metadata_extract(self, query: str) -> Dict[str, Any]:
        try:
            return self.metadata_extractor.extract(query)
        except Exception as e:
            self._log_error("Metadata extraction failed", e)
            return {}

    def _safe_embed(self, query: str):
        try:
            return self.embedder.embed(query)
        except Exception as e:
            self._log_error("Embedding failed", e)

            # Config-driven fallback strategy
            if self.config.get("fail_on_embedding_error", False):
                raise

            return []

    # --------------------------
    # Logging (Pluggable)
    # --------------------------

    def _log_error(self, message: str, error: Exception):
        if self.logger:
            self.logger.error(message, exc_info=True)
        else:
            # fallback (can be removed in prod)
            print(f"[ERROR] {message}: {str(error)}")