"""Retrieval feature ports."""

from typing import Protocol

from app.application.retrieval.dto import GenerateAnswerCommand, GeneratedAnswer


class GenerateGroundedAnswerUseCase(Protocol):
    """Generates an answer grounded in retrieved context."""

    async def execute(self, command: GenerateAnswerCommand) -> GeneratedAnswer:
        ...
