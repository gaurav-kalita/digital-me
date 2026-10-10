"""Deterministic query rewriting and expansion for retrieval."""

from typing import List


STOP_TERMS = {"what", "which", "who", "whom", "where", "when", "why", "how", "is", "are", "the", "a", "an"}


class MultiQueryRewriter:
    """Produces stable retrieval-oriented rewrites without requiring an LLM."""

    def rewrite(self, query: str, context: str = None) -> str:
        del context
        return " ".join(query.strip().split())

    def expand(self, query: str) -> List[str]:
        normalized = self.rewrite(query)
        expansions: List[str] = [normalized]

        keyword_only = " ".join(token for token in normalized.split() if token.lower() not in STOP_TERMS)
        if keyword_only and keyword_only not in expansions:
            expansions.append(keyword_only)

        architecture_variant = self._architecture_variant(normalized)
        if architecture_variant and architecture_variant not in expansions:
            expansions.append(architecture_variant)

        return expansions

    def _architecture_variant(self, query: str) -> str:
        lowered = query.lower()
        if "who am i" in lowered:
            return "profile biography experience"
        if "architecture" in lowered:
            return "%s design system components" % query
        if "project" in lowered:
            return "%s implementation delivery work" % query
        return ""
