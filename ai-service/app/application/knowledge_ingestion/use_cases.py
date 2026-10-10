"""Knowledge ingestion use cases."""

from typing import List

from app.data_layer.models import IndexedChunk
from app.data_layer.pipeline import OfflineIndexingPipeline


class BuildKnowledgeIndexUseCase:
    """Runs the offline indexing workflow."""

    def __init__(self, pipeline: OfflineIndexingPipeline):
        self.pipeline = pipeline

    def execute(self) -> List[IndexedChunk]:
        return self.pipeline.run()
