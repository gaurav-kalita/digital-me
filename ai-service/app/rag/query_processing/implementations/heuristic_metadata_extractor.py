"""Heuristic metadata extraction for the query-processing pipeline."""

import re
from typing import Dict, List


TIME_REFERENCE_PATTERN = re.compile(r"\b(today|yesterday|tomorrow|last week|next week|recent|latest)\b", re.I)


class HeuristicMetadataExtractor:
    """Extracts lightweight structured metadata without external dependencies."""

    def extract(self, query: str) -> Dict[str, object]:
        lowered = query.lower()
        tokens = [token for token in re.findall(r"[a-zA-Z0-9']+", query) if len(token) > 2]
        entities = self._extract_entities(query)

        return {
            "topic": tokens[0] if tokens else "",
            "type": self._infer_query_type(lowered),
            "time_reference": self._extract_time_reference(lowered),
            "entities": entities,
        }

    def _infer_query_type(self, lowered_query: str) -> str:
        if any(token in lowered_query for token in {"code", "function", "class", "api", "bug"}):
            return "code"
        if any(token in lowered_query for token in {"document", "docs", "readme", "architecture"}):
            return "document"
        if any(token in lowered_query for token in {"note", "notes", "memory", "profile"}):
            return "notes"
        return "general"

    def _extract_time_reference(self, lowered_query: str) -> str:
        match = TIME_REFERENCE_PATTERN.search(lowered_query)
        return match.group(1).lower() if match else ""

    def _extract_entities(self, query: str) -> List[str]:
        entities = []
        for token in re.findall(r"\b[A-Z][a-zA-Z0-9_-]+\b", query):
            if token not in entities:
                entities.append(token)
        return entities
