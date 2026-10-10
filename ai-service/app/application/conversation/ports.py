"""Conversation feature ports."""

from typing import Protocol

from app.application.conversation.dto import AnswerQuestionCommand, AnswerQuestionResult


class AnswerQuestionUseCase(Protocol):
    """Answers a user question using grounded retrieval."""

    async def execute(self, command: AnswerQuestionCommand) -> AnswerQuestionResult:
        ...
