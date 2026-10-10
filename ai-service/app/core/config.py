# app/core/config.py

import os
from dataclasses import dataclass

try:
    from dotenv import load_dotenv
except ImportError:
    load_dotenv = None


def _load_environment() -> None:
    """
    Load local environment overrides when python-dotenv is installed.

    The application must still start in environments where the dependency is
    unavailable, so dotenv remains an optional convenience rather than a hard
    runtime requirement.
    """

    if load_dotenv is not None:
        load_dotenv()


_load_environment()


# --------------------------
# RAG CONFIGS
# --------------------------

@dataclass
class QueryProcessingConfig:
    max_query_length: int = int(os.getenv("MAX_QUERY_LENGTH", 512))
    fail_on_embedding_error: bool = os.getenv("FAIL_ON_EMBEDDING_ERROR", "false").lower() == "true"


@dataclass
class CleaningConfig:
    strategy: str = os.getenv("CLEANER_TYPE", "conservative")


@dataclass
class EmbeddingConfig:
    strategy: str = os.getenv("EMBEDDER_TYPE", "auto")
    model: str = os.getenv("EMBEDDING_MODEL", "nomic-embed-text")
    dimensions: int = int(os.getenv("EMBEDDING_DIMENSIONS", 256))
    local_files_only: bool = os.getenv("EMBEDDING_LOCAL_FILES_ONLY", "true").lower() == "true"


@dataclass
class RetrievalConfig:
    top_k: int = int(os.getenv("RETRIEVAL_TOP_K", 5))
    candidate_k: int = int(os.getenv("RETRIEVAL_CANDIDATE_K", 8))
    dense_weight: float = float(os.getenv("RETRIEVAL_DENSE_WEIGHT", 0.65))
    sparse_weight: float = float(os.getenv("RETRIEVAL_SPARSE_WEIGHT", 0.35))
    backend: str = os.getenv("RETRIEVAL_BACKEND", "llamaindex")


@dataclass
class IngestionConfig:
    loader_strategy: str = os.getenv("INGESTION_LOADER_STRATEGY", "llamaindex")


@dataclass
class ChunkingConfig:
    strategy: str = os.getenv("CHUNKER_TYPE", "tiktoken")
    chunk_size_tokens: int = int(os.getenv("CHUNK_SIZE_TOKENS", 240))
    chunk_overlap_tokens: int = int(os.getenv("CHUNK_OVERLAP_TOKENS", 40))
    encoding_name: str = os.getenv("CHUNKER_ENCODING_NAME", "cl100k_base")
    huggingface_model_name: str = os.getenv("CHUNKER_HF_MODEL_NAME", "bert-base-uncased")


@dataclass
class ContextConfig:
    max_chunks: int = int(os.getenv("CONTEXT_MAX_CHUNKS", 5))
    max_tokens: int = int(os.getenv("CONTEXT_MAX_TOKENS", 900))


@dataclass
class RerankingConfig:
    enabled: bool = os.getenv("RERANKER_ENABLED", "true").lower() == "true"
    strategy: str = os.getenv("RERANKER_STRATEGY", "semantic")
    model: str = os.getenv("RERANKER_MODEL", "cross-encoder/ms-marco-MiniLM-L-6-v2")
    max_candidates: int = int(os.getenv("RERANKER_MAX_CANDIDATES", 20))
    batch_size: int = int(os.getenv("RERANKER_BATCH_SIZE", 8))
    top_k: int = int(os.getenv("RERANKER_TOP_K", 5))


@dataclass
class CacheConfig:
    enabled: bool = os.getenv("REDIS_CACHE_ENABLED", "true").lower() == "true"
    url: str = os.getenv("REDIS_URL", "redis://localhost:6379/0")
    namespace: str = os.getenv("REDIS_CACHE_NAMESPACE", "digital-me")
    retrieval_ttl_seconds: int = int(os.getenv("RETRIEVAL_CACHE_TTL_SECONDS", 3600))
    default_ttl_seconds: int = int(os.getenv("CACHE_TTL_SECONDS", 3600))


@dataclass
class GuardrailConfig:
    enabled: bool = os.getenv("GUARDRAIL_ENABLED", "false").lower() == "true"
    max_question_length: int = int(os.getenv("GUARDRAIL_MAX_QUESTION_LENGTH", 512))
    repeated_token_ratio: float = float(os.getenv("GUARDRAIL_REPEATED_TOKEN_RATIO", 0.6))
    allowed_question_patterns: tuple = tuple(
        pattern.strip()
        for pattern in os.getenv(
            "GUARDRAIL_ALLOWED_QUESTION_PATTERNS",
            "who are you,tell me about yourself,about you,about me,my past,my history,notice period,availability,current availability,what is your experience,what is my experience,what have you worked on,what have you built,what are your skills,what are your projects,what recent project have you worked on,what recent projects have you worked on,what is your recent project,what is your latest project,what are your characteristics,what are your qualities,what are your strengths,where have you worked,which companies have you worked at,what technologies have you used,what is your background,what is your career history,what roles have you held,what are your achievements,what is your tech stack,what do you do,what do you work on,tell me about my past",
        ).split(",")
        if pattern.strip()
    )
    blocked_patterns: tuple = tuple(
        pattern.strip()
        for pattern in os.getenv(
            "GUARDRAIL_BLOCKED_PATTERNS",
            "ignore previous instructions,reveal system prompt,show system prompt,developer mode,bypass safety,api key,secret key,hidden prompt",
        ).split(",")
        if pattern.strip()
    )
    output_blocked_patterns: tuple = tuple(
        pattern.strip()
        for pattern in os.getenv(
            "GUARDRAIL_OUTPUT_BLOCKED_PATTERNS",
            "system prompt,developer message,hidden prompt,api key,secret key",
        ).split(",")
        if pattern.strip()
    )
    refusal_message: str = os.getenv(
        "GUARDRAIL_REFUSAL_MESSAGE",
        "I can only answer questions about Gaurav Kalita, his work, skills, projects, and background.",
    )


# --------------------------
# MAIN SETTINGS
# --------------------------

class Settings:
    SERVICE_NAME: str = os.getenv("SERVICE_NAME", "digital-me-ai-service")
    SERVICE_VERSION: str = os.getenv("SERVICE_VERSION", "2.0.0")
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
    REQUEST_ID_HEADER: str = os.getenv("REQUEST_ID_HEADER", "X-Request-ID")
    SECRET_KEY: str = os.getenv("SECRET_KEY", "secret")
    LLM_API_KEY: str = os.getenv("LLM_API_KEY", "")
    OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")
    OPENAI_BASE_URL: str = os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1")
    OPENAI_MODEL: str = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
    VECTOR_DB_URL: str = os.getenv("VECTOR_DB_URL", "")
    OLLAMA_URL: str = os.getenv("OLLAMA_URL", "http://localhost:11434")
    OLLAMA_MODEL: str = os.getenv("OLLAMA_MODEL", "gemma3:1b")
    LLM_TYPE: str = os.getenv("LLM_TYPE", "ollama")
    DATA_DIR: str = os.getenv(
        "DATA_DIR",
        os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", "data")),
    )
    INDEX_ARTIFACT_PATH: str = os.getenv(
        "INDEX_ARTIFACT_PATH",
        os.path.abspath(
            os.path.join(os.path.dirname(__file__), "..", "..", "..", "data", ".index", "chunks.json")
        ),
    )
    VECTOR_STORE_TYPE: str = os.getenv("VECTOR_STORE_TYPE", "faiss")
    FAISS_INDEX_PATH: str = os.getenv(
        "FAISS_INDEX_PATH",
        os.path.abspath(
            os.path.join(os.path.dirname(__file__), "..", "..", "..", "data", ".index", "chunks.faiss")
        ),
    )
    FAISS_METADATA_PATH: str = os.getenv(
        "FAISS_METADATA_PATH",
        os.path.abspath(
            os.path.join(os.path.dirname(__file__), "..", "..", "..", "data", ".index", "chunks.metadata.json")
        ),
    )

    # 👇 ADD RAG CONFIGS HERE (composition, not flattening)
    cleaning: CleaningConfig = CleaningConfig()
    query: QueryProcessingConfig = QueryProcessingConfig()
    embedding: EmbeddingConfig = EmbeddingConfig()
    retrieval: RetrievalConfig = RetrievalConfig()
    ingestion: IngestionConfig = IngestionConfig()
    chunking: ChunkingConfig = ChunkingConfig()
    context: ContextConfig = ContextConfig()
    reranking: RerankingConfig = RerankingConfig()
    cache: CacheConfig = CacheConfig()
    guardrails: GuardrailConfig = GuardrailConfig()


settings = Settings()
