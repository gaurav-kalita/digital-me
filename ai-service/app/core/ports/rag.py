"""Port definitions for the online RAG flow."""

from typing import Any, Dict, Iterable, List, Protocol, Tuple

from app.data_layer.models import RetrievalResult


class QueryProcessor(Protocol):
    """Normalizes and expands user queries for retrieval."""

    def process(self, query: str) -> Dict[str, Any]:
        ...


class RetrievalGateway(Protocol):
    """Retrieves candidates for one or more rewritten queries."""

    async def retrieve(self, queries: Iterable[str]) -> List[RetrievalResult]:
        ...


class Reranker(Protocol):
    """Reorders retrieved candidates."""

    def rank(self, query: str, candidates: Iterable[RetrievalResult]) -> List[RetrievalResult]:
        ...


class ContextBuilder(Protocol):
    """Builds a token-bounded prompt context."""

    def build(self, query: str, candidates: List[RetrievalResult]) -> Tuple[str, List[RetrievalResult]]:
        ...


class LLMProvider(Protocol):
    """Generates the final grounded answer."""

    async def generate(self, prompt: str) -> str:
        ...
