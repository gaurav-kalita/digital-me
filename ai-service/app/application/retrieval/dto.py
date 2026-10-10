"""DTOs for the retrieval feature."""

from dataclasses import dataclass
from typing import Any, Dict, List

from app.data_layer.models import RetrievalResult


@dataclass(frozen=True)
class GenerateAnswerCommand:
    """Input for the grounded-answer generation workflow."""

    query: str


@dataclass(frozen=True)
class GeneratedAnswer:
    """Output of the retrieval-plus-generation workflow."""

    answer: str
    prompt: str
    context_items: List[RetrievalResult]
    processed_query: Dict[str, Any]
