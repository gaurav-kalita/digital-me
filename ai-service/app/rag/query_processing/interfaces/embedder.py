# interfaces/embedder.py

from abc import ABC, abstractmethod
from typing import List

class IEmbedder(ABC):
    @abstractmethod
    def embed(self, text: str) -> List[float]:
        pass