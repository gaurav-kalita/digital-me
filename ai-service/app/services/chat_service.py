from typing import Any, Optional

from app.application.conversation.dto import AnswerQuestionCommand
from app.application.guardrails.service import GuardrailService
from app.application.conversation.ports import AnswerQuestionUseCase
from app.core.exceptions import AIServiceError, GuardrailViolation
from app.core.logger import logger
from app.models.chat import ChatResponse


class _LegacyAnswerQuestionAdapter:
    """Compatibility adapter for legacy tests and transitional callers."""

    def __init__(self, rag_pipeline):
        self.rag_pipeline = rag_pipeline

    async def execute(self, command: AnswerQuestionCommand):
        rag_result = await self.rag_pipeline.answer(command.question)
        if not getattr(rag_result, "context_items", []):
            return type(
                "AnswerQuestionResult",
                (),
                {
                    "answer": "I don't have enough information to answer that yet.",
                    "sources": [],
                    "query": rag_result.processed_query.get("rewritten_query", command.question),
                },
            )()

        return type(
            "AnswerQuestionResult",
            (),
            {
                "answer": rag_result.answer,
                "sources": [item.to_source_label() for item in rag_result.context_items],
                "query": rag_result.processed_query.get("rewritten_query", command.question),
            },
        )()


class ChatService:
    def __init__(
        self,
        answer_question: Optional[AnswerQuestionUseCase] = None,
        rag_pipeline=None,
        guardrails: Optional[GuardrailService] = None,
    ):
        self.guardrails = guardrails or GuardrailService()
        if answer_question is None:
            if rag_pipeline is None:
                raise ValueError("ChatService requires an answer use case or a legacy rag_pipeline")
            answer_question = _LegacyAnswerQuestionAdapter(rag_pipeline)
        self.answer_question = answer_question

    async def chat(self, question: str, user: Optional[Any] = None) -> ChatResponse:
        try:
            safe_question = self.guardrails.validate_question(question)
            result = await self.answer_question.execute(
                AnswerQuestionCommand(question=safe_question, user_id=self._get_user_id(user))
            )
            return ChatResponse(
                answer=self._post_process(self.guardrails.sanitize_answer(result.answer)),
                sources=result.sources,
                query=result.query,
            )
        except GuardrailViolation:
            raise
        except AIServiceError:
            raise
        except Exception as exc:
            logger.bind(user_id=self._get_user_id(user)).opt(exception=exc).error("ChatService failed")
            raise AIServiceError("Failed to process request") from exc

    async def ask(self, question: str, user_id: str) -> str:
        response = await self.chat(question, user={"sub": user_id})
        return response.answer

    def _get_user_id(self, user: Optional[Any]) -> str:
        if isinstance(user, dict):
            return str(user.get("sub", "anonymous"))
        return "anonymous"

    def _post_process(self, response: str) -> str:
        return response.strip()
