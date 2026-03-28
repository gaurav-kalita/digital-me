class LLMQueryRewriter:
    def __init__(self, llm_client, base_context: str):
        self.llm = llm_client
        self.base_context = base_context

    def rewrite(self, query: str, runtime_context: str = None) -> str:
        full_context = self._build_context(runtime_context)

        prompt = f"""
You are rewriting a user query for semantic search.

User Context:
{full_context}

Rules:
- Make it specific
- Resolve ambiguity
- Expand implicit references
- Keep it concise

Query: {query}

Rewritten Query:
"""

        try:
            response = self.llm.generate(prompt)
            return response.strip()
        except Exception:
            return query  # fallback