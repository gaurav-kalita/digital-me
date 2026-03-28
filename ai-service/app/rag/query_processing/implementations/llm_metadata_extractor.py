# implementations/llm_metadata_extractor.py

import json

class LLMMetadataExtractor:
    def __init__(self, llm_client):
        self.llm = llm_client

    def extract(self, query: str) -> dict:
        prompt = f"""
Extract structured metadata from the query.

Return JSON only.

Fields:
- topic
- type (code, notes, document, general)
- time_reference (if any)
- entities (list)

Query: {query}
"""

        response = self.llm.generate(prompt)

        try:
            return json.loads(response)
        except:
            return {}