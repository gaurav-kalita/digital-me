"""DTOs for the conversation feature."""

from dataclasses import dataclass, field
from typing import Any, Dict, List


@dataclass(frozen=True)
class AnswerQuestionCommand:
    """Input for answering a grounded user question."""

    question: str
    user_id: str = "anonymous"


@dataclass(frozen=True)
class AnswerQuestionResult:
    """Output returned by the conversation use case."""

    answer: str
    sources: List[str] = field(default_factory=list)
    query: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)
