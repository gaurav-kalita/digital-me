from typing import List
from app.rag.query_enhancer import QueryEnhancer
from app.rag.retriever import Retriever
from app.rag.prompt_builder import PromptBuilder
from app.rag.llm_client import LLMClient
from app.core.logger import logger
from app.core.exceptions import AIServiceError

class ChatService:
    def __init__(
        self,
        retriever: Retriever,
        llm: LLMClient,
        prompt_builder: PromptBuilder,
        query_enhancer: QueryEnhancer,
    ):
        self.retriever = retriever
        self.llm = llm
        self.prompt_builder = prompt_builder
        self.query_enhancer = query_enhancer

    async def ask(self, question: str, user_id: str) -> str:
        try:
            logger.info("Chat request received", extra={"user_id": user_id})

            # 1. Enhance query
            enhanced_query = await self.query_enhancer.enhance(question)
            logger.debug("Query enhanced", extra={"enhanced_query": enhanced_query})

            # 2. Retrieve documents
            docs = self.retriever.retrieve(enhanced_query)
            if not docs:
                logger.warning("No documents found", extra={"query": question})
                return "I don’t have enough information to answer that."

            # 3. Build prompt
            prompt = self.prompt_builder.build(question, docs)

            # 4. Call LLM
            response = await self.llm.generate(prompt)

            # 5. Post-processing
            final_response = self._post_process(response)

            logger.info("Response generated successfully")
            return final_response

        except Exception as e:
            logger.error("ChatService failed", exc_info=True)
            raise AIServiceError("Failed to process request") from e

    def _post_process(self, response: str) -> str:
        # Add any sanitization / formatting
        return response.strip()