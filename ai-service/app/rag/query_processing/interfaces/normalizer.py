# interfaces/normalizer.py

from abc import ABC, abstractmethod

class IQueryNormalizer(ABC):
    @abstractmethod
    def normalize(self, query: str) -> str:
        pass