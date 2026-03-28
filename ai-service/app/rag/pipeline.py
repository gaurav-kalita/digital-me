from typing import List, Any

class RAGPipeline:
    async def enhance_query(self, query: str) -> str:
        # Placeholder for query enhancement
        return query

    async def build_prompt(self, query: str, docs: List[Any]) -> str:
        # Placeholder for prompt building
        return f"Context: {docs}\nQuestion: {query}"
