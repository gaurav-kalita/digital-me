from typing import Any, Optional

from app.core.exceptions import AIServiceError
from app.core.logger import logger
from app.models.chat import ChatResponse
from app.rag.llm_client import LLMClient
from app.rag.pipeline import RAGPipeline


class ChatService:
    def __init__(
        self,
        llm: Optional[Any] = None,
        rag_pipeline: Optional[RAGPipeline] = None,
    ):
        self.llm = llm or LLMClient()
        self.rag_pipeline = rag_pipeline or RAGPipeline()

    async def chat(self, question: str, user: Optional[Any] = None) -> ChatResponse:
        try:
            user_id = self._get_user_id(user)
            logger.info("Chat request received", extra={"user_id": user_id})

            rag_result = await self.rag_pipeline.prepare(question)
            docs = rag_result.context_items

            if not docs:
                logger.warning("No documents found", extra={"query": question, "user_id": user_id})
                return ChatResponse(
                    answer="I don't have enough information to answer that yet.",
                    sources=[],
                    query=rag_result.processed_query.get("rewritten_query", question),
                )

            response = await self.llm.generate(rag_result.prompt)

            logger.info("Response generated successfully", extra={"user_id": user_id})
            return ChatResponse(
                answer=self._post_process(response),
                sources=[doc.to_source_label() for doc in docs],
                query=rag_result.processed_query.get("rewritten_query", question),
            )
        except AIServiceError:
            raise
        except Exception as exc:
            logger.error("ChatService failed", exc_info=True)
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
