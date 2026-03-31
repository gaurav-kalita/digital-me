# app/core/config.py

import os
from dotenv import load_dotenv
from dataclasses import dataclass

load_dotenv()


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


@dataclass
class RetrievalConfig:
    top_k: int = int(os.getenv("RETRIEVAL_TOP_K", 5))
    candidate_k: int = int(os.getenv("RETRIEVAL_CANDIDATE_K", 8))
    dense_weight: float = float(os.getenv("RETRIEVAL_DENSE_WEIGHT", 0.65))
    sparse_weight: float = float(os.getenv("RETRIEVAL_SPARSE_WEIGHT", 0.35))


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
    top_k: int = int(os.getenv("RERANKER_TOP_K", 5))


# --------------------------
# MAIN SETTINGS
# --------------------------

class Settings:
    SECRET_KEY: str = os.getenv("SECRET_KEY", "secret")
    LLM_API_KEY: str = os.getenv("LLM_API_KEY", "")
    VECTOR_DB_URL: str = os.getenv("VECTOR_DB_URL", "")
    OLLAMA_URL: str = os.getenv("OLLAMA_URL", "http://localhost:11434")
    OLLAMA_MODEL: str = os.getenv("OLLAMA_MODEL", "gemma:3b")
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
    chunking: ChunkingConfig = ChunkingConfig()
    context: ContextConfig = ContextConfig()
    reranking: RerankingConfig = RerankingConfig()


settings = Settings()
