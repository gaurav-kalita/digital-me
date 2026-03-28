# interfaces/rewriter.py

from abc import ABC, abstractmethod

class IQueryRewriter(ABC):
    @abstractmethod
    def rewrite(self, query: str, context: str = None) -> str:
        pass