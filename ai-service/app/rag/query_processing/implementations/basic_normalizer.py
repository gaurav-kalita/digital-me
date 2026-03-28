# implementations/basic_normalizer.py

import re

class BasicQueryNormalizer:
    def normalize(self, query: str) -> str:
        query = query.lower().strip()

        # remove extra spaces
        query = re.sub(r'\s+', ' ', query)

        # basic punctuation cleanup
        query = re.sub(r'[^\w\s?]', '', query)

        return query