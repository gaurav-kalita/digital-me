"""Context selection and prompt construction for the online RAG pipeline."""

from typing import List, Tuple

from app.core.config import settings
from app.data_layer.models import RetrievalResult


class ContextBuilder:
    """Builds a token-budgeted, deduplicated context window for generation."""

    def __init__(self, max_chunks: int = None, max_tokens: int = None):
        self.max_chunks = max_chunks or settings.context.max_chunks
        self.max_tokens = max_tokens or settings.context.max_tokens

    def build(self, query: str, candidates: List[RetrievalResult]) -> Tuple[str, List[RetrievalResult]]:
        selected = []
        seen_chunks = set()
        token_budget = 0

        for item in candidates:
            if item.chunk_id in seen_chunks:
                continue
            if len(selected) >= self.max_chunks:
                break
            if token_budget + item.token_count > self.max_tokens:
                continue

            selected.append(item)
            seen_chunks.add(item.chunk_id)
            token_budget += item.token_count

        prompt = self._build_prompt(query=query, context=selected)
        return prompt, selected

    def _build_prompt(self, query: str, context: List[RetrievalResult]) -> str:
        context_lines = []
        for item in context:
            context_lines.append("SOURCE: %s\n%s" % (item.title, item.text))

        response_guidance = self._response_guidance(query)
        prompt = (
            "SYSTEM:\n"
            "You are the personal AI assistant for Gaurav Kalita.\n"
            "Answer only questions about Gaurav Kalita, his work, skills, projects, background, and experience.\n"
            "If the user asks anything unrelated to Gaurav Kalita, refuse briefly and say you can only answer questions about him.\n"
            "%s\n"
            "Use only the provided context. If the answer is not present, say you do not know.\n\n"
            "CONTEXT:\n%s\n\n"
            "QUESTION:\n%s\n"
        ) % (
            response_guidance,
            "\n\n".join(context_lines) or "No relevant context retrieved.",
            query,
        )
        return prompt

    def _response_guidance(self, query: str) -> str:
        normalized = query.lower()

        if any(keyword in normalized for keyword in ("characteristic", "characteristics", "qualities", "strengths", "personality", "traits")):
            return (
                "When the user asks about characteristics, qualities, strengths, or traits, answer only with facts explicitly supported by the context. "
                "Do not infer personality from job titles, technologies, or company names. "
                "Use a short markdown bullet list with each bullet in the form 'Trait: evidence'. "
                "If the context does not directly state a characteristic, say you do not know."
            )

        return (
            "When the user asks about experience, include company names, roles, dates, technologies, and measurable impact. "
            "Prefer a clean markdown structure with short headings, bullet points, and concise sections when that improves clarity. "
            "Keep the answer specific and useful. Do not be vague. "
            "Respond in markdown. Avoid long paragraphs. Use bullets or short sections for readability."
        )
