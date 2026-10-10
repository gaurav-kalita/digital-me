"""Application-layer safety controls for user input and model output."""

from __future__ import annotations

import re
from collections import Counter
from typing import Iterable, Tuple

from app.core.config import settings
from app.core.exceptions import GuardrailViolation
from app.core.logger import logger


class GuardrailService:
    """Validates user questions and sanitizes model responses."""

    def __init__(
        self,
        max_question_length: int | None = None,
        repeated_token_ratio: float | None = None,
        allowed_question_patterns: Iterable[str] | None = None,
        blocked_patterns: Iterable[str] | None = None,
        output_blocked_patterns: Iterable[str] | None = None,
        refusal_message: str | None = None,
        enabled: bool | None = None,
    ):
        self.enabled = settings.guardrails.enabled if enabled is None else enabled
        self.max_question_length = max_question_length or settings.guardrails.max_question_length
        self.repeated_token_ratio = repeated_token_ratio or settings.guardrails.repeated_token_ratio
        self.allowed_question_patterns = self._compile_patterns(
            allowed_question_patterns or settings.guardrails.allowed_question_patterns
        )
        self.blocked_patterns = self._compile_patterns(blocked_patterns or settings.guardrails.blocked_patterns)
        self.output_blocked_patterns = self._compile_patterns(
            output_blocked_patterns or settings.guardrails.output_blocked_patterns
        )
        self.refusal_message = refusal_message or settings.guardrails.refusal_message
        self.topic_keywords = {
            keyword.strip().lower()
            for keyword in (
                "experience",
                "project",
                "projects",
                "work",
                "worked",
                "career",
                "background",
                "role",
                "roles",
                "skill",
                "skills",
                "technology",
                "technologies",
                "stack",
                "company",
                "companies",
                "characteristic",
                "characteristics",
                "qualities",
                "strengths",
                "notice period",
                "availability",
                "recent",
                "latest",
                "current",
                "portfolio",
                "resume",
            )
        }
        self.subject_anchor_patterns = self._compile_patterns(
            (
                r"\bgaurav\b",
                r"\bkalita\b",
                r"\byou(?:r|rself)?\b",
                r"\bmy(?:self)?\b",
                r"\bme\b",
                r"\babout you\b",
                r"\babout me\b",
            )
        )
        self.identity_question_patterns = self._compile_patterns(
            (
                r"^\s*who\s+(is|are)\s+(gaurav|kalita|you|yourself|me)\b",
                r"^\s*what\s+(is|are)\s+(gaurav|kalita|you|yourself|me)\b",
                r"^\s*tell\s+me\s+about\s+(gaurav|kalita|you|yourself|me)\b",
                r"^\s*describe\s+(gaurav|kalita|you|yourself|me)\b",
            )
        )
        self.general_question_patterns = self._compile_patterns(
            (
                r"^\s*what\s+about\b",
                r"^\s*tell\s+me\b",
                r"^\s*show\s+me\b",
                r"^\s*give\s+me\b",
                r"^\s*share\b",
                r"^\s*explain\b",
                r"^\s*describe\b",
                r"^\s*how\s+about\b",
                r"^\s*which\b",
                r"^\s*where\b",
                r"^\s*when\b",
                r"^\s*why\b",
            )
        )

    def validate_question(self, question: str) -> str:
        normalized = " ".join(question.strip().split())
        if not self.enabled:
            return normalized

        if len(normalized) < 3:
            raise GuardrailViolation("Question too short.")

        if len(normalized) > self.max_question_length:
            raise GuardrailViolation(
                f"Question exceeds the maximum allowed length of {self.max_question_length} characters."
            )

        if self._matches_blocked_pattern(normalized, self.blocked_patterns):
            raise GuardrailViolation(self.refusal_message)

        if self._looks_like_repetition(normalized):
            raise GuardrailViolation("Question appears to be repetitive or malformed.")

        if not self._is_about_gaurav(normalized):
            raise GuardrailViolation(self.refusal_message)

        return normalized

    def sanitize_answer(self, answer: str) -> str:
        if not self.enabled:
            return answer

        cleaned = self._normalize_plain_text(answer)
        if not cleaned:
            return self.refusal_message

        if self._matches_blocked_pattern(cleaned, self.output_blocked_patterns):
            logger.warning("Potential prompt leakage blocked in model output")
            return self.refusal_message

        return cleaned

    def _compile_patterns(self, patterns: Iterable[str]) -> Tuple[re.Pattern[str], ...]:
        return tuple(re.compile(pattern, re.IGNORECASE) for pattern in patterns)

    def _matches_blocked_pattern(self, text: str, patterns: Tuple[re.Pattern[str], ...]) -> bool:
        return any(pattern.search(text) for pattern in patterns)

    def _looks_like_repetition(self, text: str) -> bool:
        tokens = [token.lower() for token in text.split() if token.strip()]
        if len(tokens) < 6:
            return False

        counts = Counter(tokens)
        most_common_count = counts.most_common(1)[0][1]
        return (most_common_count / len(tokens)) >= self.repeated_token_ratio

    def _is_about_gaurav(self, text: str) -> bool:
        if self._matches_blocked_pattern(text, self.blocked_patterns):
            return False

        has_subject_anchor = self._matches_blocked_pattern(text, self.subject_anchor_patterns)
        if not has_subject_anchor:
            return False

        if self._matches_blocked_pattern(text, self.identity_question_patterns):
            return True

        if self._matches_blocked_pattern(text, self.allowed_question_patterns):
            return True

        normalized = text.lower()
        has_topic_keyword = any(keyword in normalized for keyword in self.topic_keywords)
        if has_topic_keyword:
            return True

        has_general_question_form = self._matches_blocked_pattern(text, self.general_question_patterns)
        return has_general_question_form

    def _normalize_plain_text(self, text: str) -> str:
        normalized_lines = []
        previous_blank = False

        for raw_line in text.replace("\r\n", "\n").replace("\r", "\n").split("\n"):
            line = re.sub(r"[ \t]+", " ", raw_line).strip()
            if not line:
                if not previous_blank:
                    normalized_lines.append("")
                previous_blank = True
                continue

            normalized_lines.append(line)
            previous_blank = False

        return "\n".join(normalized_lines).strip()
