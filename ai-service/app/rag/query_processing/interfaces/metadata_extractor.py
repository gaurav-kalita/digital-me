# interfaces/metadata_extractor.py

from abc import ABC, abstractmethod
from typing import Dict

class IMetadataExtractor(ABC):
    @abstractmethod
    def extract(self, query: str) -> Dict:
        pass