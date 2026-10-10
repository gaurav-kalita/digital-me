"""Bootstrap composition root for the feature-oriented application layer."""

from functools import lru_cache
from typing import Optional

from app.application.conversation.use_cases import DefaultAnswerQuestionUseCase
from app.application.guardrails.service import GuardrailService
from app.application.form_filling.use_cases import DefaultPlanFormFillUseCase
from app.application.knowledge_ingestion.use_cases import BuildKnowledgeIndexUseCase
from app.application.retrieval.use_cases import RetrievalWorkflow
from app.core.config import settings
from app.data_layer.chunker import ChunkerFactory
from app.data_layer.cleaner import CleanerFactory
from app.data_layer.embedder import build_default_embedder
from app.data_layer.filesystem import FileSystemDocumentLoader
from app.data_layer.pipeline import JsonArtifactStore, OfflineIndexingPipeline
from app.infrastructure.cache.redis_cache import NullCacheStore, RedisCacheStore
from app.infrastructure.llamaindex import CompositeDocumentLoader, LlamaIndexDocumentLoader, LlamaIndexRetrievalGateway
from app.providers.factory import ProviderFactory
from app.rag.context_builder import ContextBuilder
from app.rag.query_processing.factory import build_query_processing_pipeline
from app.rag.reranker import build_default_reranker
from app.rag.retriever import Retriever
from app.rag.vector_store import build_default_vector_store
from app.repositories.vector_repository import VectorRepository
from app.services.chat_service import ChatService


def build_artifact_store() -> JsonArtifactStore:
    return JsonArtifactStore(settings.INDEX_ARTIFACT_PATH)


def build_document_loader(data_dir: Optional[str] = None):
    selected_data_dir = data_dir or settings.DATA_DIR
    native_loader = FileSystemDocumentLoader(selected_data_dir)
    loader_strategy = settings.ingestion.loader_strategy.lower()

    if loader_strategy in {"hybrid", "llamaindex"}:
        return CompositeDocumentLoader(
            [
                native_loader,
                LlamaIndexDocumentLoader(selected_data_dir),
            ]
        )

    return native_loader


@lru_cache(maxsize=1)
def build_cache_store():
    if not settings.cache.enabled:
        return NullCacheStore()

    return RedisCacheStore(
        url=settings.cache.url,
        namespace=settings.cache.namespace,
        required=False,
    )


def build_offline_indexing_pipeline(
    data_dir: Optional[str] = None,
    artifact_path: Optional[str] = None,
    embedding_model: Optional[str] = None,
) -> OfflineIndexingPipeline:
    return OfflineIndexingPipeline(
        loader=build_document_loader(data_dir),
        cleaner=CleanerFactory.create(),
        chunker=ChunkerFactory.create(),
        embedder=build_default_embedder(embedding_model or settings.embedding.model),
        vector_store=build_default_vector_store(),
        artifact_store=JsonArtifactStore(artifact_path or settings.INDEX_ARTIFACT_PATH),
    )


def build_knowledge_index_use_case() -> BuildKnowledgeIndexUseCase:
    return BuildKnowledgeIndexUseCase(
        pipeline=build_offline_indexing_pipeline(
            data_dir=settings.DATA_DIR,
            artifact_path=settings.INDEX_ARTIFACT_PATH,
            embedding_model=settings.embedding.model,
        )
    )


def build_vector_repository() -> VectorRepository:
    return VectorRepository(
        vector_store=build_default_vector_store(),
        embedder=build_default_embedder(settings.embedding.model),
        artifact_store=build_artifact_store(),
        cache_store=build_cache_store(),
        rebuild_pipeline_factory=lambda: build_offline_indexing_pipeline(
            data_dir=settings.DATA_DIR,
            artifact_path=settings.INDEX_ARTIFACT_PATH,
            embedding_model=settings.embedding.model,
        ),
    )


def build_retrieval_workflow() -> RetrievalWorkflow:
    provider, retriever, reranker, context_builder, query_processor = build_rag_stack()
    return RetrievalWorkflow(
        query_processor=query_processor,
        retriever=retriever,
        reranker=reranker,
        context_builder=context_builder,
        provider=provider,
    )


def build_llamaindex_retriever() -> LlamaIndexRetrievalGateway:
    return LlamaIndexRetrievalGateway(
        document_loader=build_document_loader(),
        embedder=build_default_embedder(settings.embedding.model),
        top_k=settings.retrieval.candidate_k,
        chunk_size=settings.chunking.chunk_size_tokens,
        chunk_overlap=settings.chunking.chunk_overlap_tokens,
    )


def build_guardrail_service() -> GuardrailService:
    return GuardrailService()


def build_answer_question_use_case() -> DefaultAnswerQuestionUseCase:
    return DefaultAnswerQuestionUseCase(
        generator=build_retrieval_workflow(),
        guardrails=build_guardrail_service(),
    )


@lru_cache(maxsize=1)
def build_chat_service() -> ChatService:
    return ChatService(answer_question=build_answer_question_use_case(), guardrails=build_guardrail_service())


def build_form_fill_use_case() -> DefaultPlanFormFillUseCase:
    provider, retriever, reranker, context_builder, query_processor = build_rag_stack()
    return DefaultPlanFormFillUseCase(
        query_processor=query_processor,
        retriever=retriever,
        reranker=reranker,
        context_builder=context_builder,
        provider=provider,
    )


def build_rag_stack():
    provider = ProviderFactory.create()
    retriever_backend = settings.retrieval.backend.lower()
    retriever = build_llamaindex_retriever() if retriever_backend == "llamaindex" else Retriever(repository=build_vector_repository())
    return (
        provider,
        retriever,
        build_default_reranker(),
        ContextBuilder(),
        build_query_processing_pipeline(provider=provider),
    )
