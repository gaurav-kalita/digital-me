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
class EmbeddingConfig:
    model: str = os.getenv("EMBEDDING_MODEL", "nomic-embed-text")


@dataclass
class RetrievalConfig:
    top_k: int = int(os.getenv("RETRIEVAL_TOP_K", 5))


# --------------------------
# MAIN SETTINGS
# --------------------------

class Settings:
    SECRET_KEY: str = os.getenv("SECRET_KEY", "secret")
    LLM_API_KEY: str = os.getenv("LLM_API_KEY", "")
    VECTOR_DB_URL: str = os.getenv("VECTOR_DB_URL", "")
    OLLAMA_URL: str = os.getenv("OLLAMA_URL", "http://localhost:11434")
    OLLAMA_MODEL: str = os.getenv("OLLAMA_MODEL", "gemma:3b")

    # 👇 ADD RAG CONFIGS HERE (composition, not flattening)
    query: QueryProcessingConfig = QueryProcessingConfig()
    embedding: EmbeddingConfig = EmbeddingConfig()
    retrieval: RetrievalConfig = RetrievalConfig()


settings = Settings()