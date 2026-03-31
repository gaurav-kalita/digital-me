"""Context selection and prompt construction for the online RAG pipeline."""

from typing import Iterable, List, Tuple

from app.core.config import settings
from app.data_layer.models import RetrievalResult


class ContextBuilder:
    """Builds a token-budgeted, deduplicated context window for generation."""

    def __init__(self, max_chunks: int = None, max_tokens: int = None):
        self.max_chunks = max_chunks or settings.context.max_chunks
        self.max_tokens = max_tokens or settings.context.max_tokens

    def build(self, query: str, candidates: Iterable[RetrievalResult]) -> Tuple[str, List[RetrievalResult]]:
        selected: List[RetrievalResult] = []
        token_budget = 0
        seen_documents = set()

        for candidate in candidates:
            if len(selected) >= self.max_chunks:
                break
            if candidate.document_id in seen_documents:
                continue
            if token_budget + candidate.token_count > self.max_tokens:
                continue

            selected.append(candidate)
            seen_documents.add(candidate.document_id)
            token_budget += candidate.token_count

        context_lines = []
        for item in selected:
            context_lines.append("[Source: %s]\n%s" % (item.title, item.text))

        context = "\n\n".join(context_lines)
        prompt = self._build_prompt(query=query, context=context)
        return prompt, selected

    def _build_prompt(self, query: str, context: str) -> str:
        return (
            "SYSTEM:\n"
            "Use only the provided context. If the answer is not supported by the context, say so clearly.\n\n"
            "CONTEXT:\n"
            "%s\n\n"
            "QUESTION:\n"
            "%s"
        ) % (context or "No relevant context was found.", query)
