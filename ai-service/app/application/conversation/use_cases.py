"""Conversation use cases."""

from app.application.conversation.dto import AnswerQuestionCommand, AnswerQuestionResult
from app.application.guardrails.service import GuardrailService
from app.application.retrieval.dto import GenerateAnswerCommand
from app.application.retrieval.ports import GenerateGroundedAnswerUseCase
from app.core.exceptions import AIServiceError, GuardrailViolation
from app.core.logger import logger


class DefaultAnswerQuestionUseCase:
    """Application use case for answering a chat question."""

    def __init__(self, generator: GenerateGroundedAnswerUseCase, guardrails: GuardrailService = None):
        self.generator = generator
        self.guardrails = guardrails or GuardrailService()

    async def execute(self, command: AnswerQuestionCommand) -> AnswerQuestionResult:
        try:
            logger.info("Chat request received", extra={"user_id": command.user_id})
            safe_question = self.guardrails.validate_question(command.question)
            result = await self.generator.execute(GenerateAnswerCommand(query=safe_question))

            if not result.context_items:
                logger.warning("No documents found", extra={"query": command.question, "user_id": command.user_id})
                return AnswerQuestionResult(
                    answer="I don't have enough information to answer that yet.",
                    sources=[],
                    query=result.processed_query.get("rewritten_query", safe_question),
                    metadata=result.processed_query.get("metadata", {}),
                )

            logger.info("Response generated successfully", extra={"user_id": command.user_id})
            return AnswerQuestionResult(
                answer=self.guardrails.sanitize_answer(result.answer),
                sources=[item.to_source_label() for item in result.context_items],
                query=result.processed_query.get("rewritten_query", safe_question),
                metadata=result.processed_query.get("metadata", {}),
            )
        except AIServiceError:
            raise
        except GuardrailViolation:
            raise
        except Exception as exc:
            logger.bind(
                exception_type=type(exc).__name__,
                exception_message=str(exc),
                user_id=command.user_id,
            ).opt(exception=exc).error("AnswerQuestionUseCase failed")
            raise AIServiceError("Failed to process request") from exc
