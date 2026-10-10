"""Composition helpers for the query-processing pipeline."""

from app.core.config import settings
from app.core.logger import logger
from app.data_layer.embedder import build_default_embedder
from app.providers import BaseLLMProvider
from app.rag.query_processing.implementations.basic_normalizer import BasicQueryNormalizer
from app.rag.query_processing.implementations.heuristic_metadata_extractor import HeuristicMetadataExtractor
from app.rag.query_processing.implementations.multi_query_rewriter import MultiQueryRewriter
from app.rag.query_processing.pipeline import QueryProcessingPipeline


def build_query_processing_pipeline(provider: BaseLLMProvider = None) -> QueryProcessingPipeline:
    """Build the default query-processing pipeline for the online RAG flow."""

    del provider
    embedder = build_default_embedder(settings.embedding.model)
    logger.info("Initialized query-processing pipeline", extra={"embedder": type(embedder).__name__})

    return QueryProcessingPipeline(
        normalizer=BasicQueryNormalizer(),
        rewriter=MultiQueryRewriter(),
        embedder=embedder,
        metadata_extractor=HeuristicMetadataExtractor(),
        config={
            "max_query_length": settings.query.max_query_length,
            "fail_on_embedding_error": settings.query.fail_on_embedding_error,
        },
        logger=logger,
    )
