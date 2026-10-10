from dataclasses import dataclass
from typing import List, Dict, Any

@dataclass
class ProcessedQuery:
    original_query: str
    normalized_query: str
    rewritten_query: str
    embedding: List[float]
    metadata: Dict[str, Any]
    queries: List[str]
