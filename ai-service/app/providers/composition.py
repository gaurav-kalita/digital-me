"""Backward-compatible wrapper around the bootstrap composition root."""

from app.bootstrap.composition import (
    build_answer_question_use_case,
    build_artifact_store,
    build_chat_service,
    build_knowledge_index_use_case,
    build_offline_indexing_pipeline,
    build_retrieval_workflow,
    build_vector_repository,
)

__all__ = [
    "build_answer_question_use_case",
    "build_artifact_store",
    "build_chat_service",
    "build_knowledge_index_use_case",
    "build_offline_indexing_pipeline",
    "build_retrieval_workflow",
    "build_vector_repository",
]
