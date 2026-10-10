# Digital Me AI Service

## Overview

LlamaIndex-first FastAPI RAG backend with a production-oriented composition:

1. Offline pipeline for ingestion, cleaning, chunking, embedding, and artifact generation
2. Online pipeline for query processing, LlamaIndex-backed retrieval, reranking, context building, and generation

The goal is to keep ingestion concerns separate from serving concerns so we can
scale retrieval quality without rewriting the API layer.

The service follows a clean-architecture dependency rule:

- entry points depend on application services
- application services depend on ports
- infrastructure implements those ports
- `app/bootstrap/composition.py` is the composition root
- `app/infrastructure/llamaindex/` is the adapter boundary for LlamaIndex-specific code

The current runtime is also shifting toward a feature-based structure:

- `application/conversation`
- `application/retrieval`
- `application/knowledge_ingestion`
- `domain/identity_profile`
- `bootstrap/composition.py`

Redis acts as the retrieval cache, and the online reranker uses a semantic
cross-encoder when the model is available, with a deterministic lexical fallback
if it is not.

The service health endpoint now distinguishes between:

- `healthy`: critical data and index prerequisites are available
- `degraded`: noncritical dependencies such as Redis are unavailable or the index is stale
- `503`: critical readiness checks fail

The service also exposes a structured form-planning endpoint at `POST /forms/plan`
for browser automation clients. It returns a JSON fill plan for the fields the
extension scans from the current page.

## Architecture

### Offline pipeline

The offline pipeline lives in `app/data_layer` and runs:

`raw files -> normalization -> chunking -> embedding -> persisted index artifact`

Key modules:

- `filesystem.py`: loads `.txt`, `.md`, and `.json` source documents from `DATA_DIR`
- `cleaner/`: pluggable document cleaning strategies
- `chunker/`: token-aware overlapping chunking strategies selected from configuration
- `embedder/`: pluggable embedding strategies with deterministic fallback
- `pipeline.py`: offline processor that writes indexed chunk artifacts
- `index.py`: hybrid search implementation used by the online layer

The offline pipeline now persists vectors into a FAISS-backed vector store and
also writes a readable JSON artifact for debugging and rebuild visibility.

Primary persistence:

- `FAISS_INDEX_PATH`: dense vector index
- `FAISS_METADATA_PATH`: chunk metadata sidecar

Secondary artifact:

- `INDEX_ARTIFACT_PATH`: human-readable snapshot of indexed chunks

### Online pipeline

The online RAG path lives in `app/rag` and runs:

`query -> query processing -> retrieval -> reranking -> context building -> LLM`

Key modules:

- `pipeline.py`: orchestrates query processing, retrieval, reranking, context building, and provider invocation
- `retriever.py`: executes search across one or more query variants
- `reranker.py`: improves precision over retriever candidates
- `context_builder.py`: builds a token-budgeted prompt
- `vector_store/`: pluggable vector database backends owned by the retrieval subsystem
- `providers/`: pluggable generation providers such as Ollama and OpenAI

The API entrypoint calls `ChatService`, which delegates to the RAG pipeline end to end.
Dependencies are wired in `app/bootstrap/composition.py` rather than being
constructed inside handlers or services.

The live runtime path goes through feature use cases first and uses the older
technical packages as adapters behind that layer. The default
retrieval path is LlamaIndex-first so the project behaves like the current
service while using the production-oriented framework as the primary retrieval
engine.

### LlamaIndex adapter

LlamaIndex is available behind an adapter layer for optional experimentation
without replacing the existing native pipeline.

Use it when you want:

- broader document ingestion via `INGESTION_LOADER_STRATEGY=llamaindex`
- a LlamaIndex retrieval backend via `RETRIEVAL_BACKEND=llamaindex`
- richer source metadata for citations in retrieval results

The default behavior is LlamaIndex-first while keeping FAISS
and the artifact store for deterministic local persistence.

## Folder structure

```text
ai-service/
  app/
    application/
      conversation/
        dto.py
        ports.py
        use_cases.py
      retrieval/
        dto.py
        ports.py
        use_cases.py
      knowledge_ingestion/
        use_cases.py
    api/
      deps.py
      endpoints/
        chat.py
        health.py
    bootstrap/
      composition.py
    core/
      config.py
      exceptions.py
      logger.py
      security.py
      ports/
        data_access.py
        rag.py
    data_layer/
      cleaner/
      chunker/
      embedder/
      filesystem.py
      index.py
      interfaces.py
      models.py
      pipeline.py
    domain/
      identity_profile/
        entities.py
    models/
      chat.py
      user.py
    providers/
      base.py
      composition.py
      factory.py
      ollama_provider.py
      openai_provider.py
    rag/
      context_builder.py
      pipeline.py
      reranker.py
      retriever.py
      vector_store/
        base.py
        factory.py
        faiss_store.py
      query_processing/
        ...
    repositories/
      vector_repository.py
    services/
      chat_service.py
    main.py
  scripts/
    rebuild_index.py
  tests/
    test_chat.py
    test_data_layer.py
    test_rag_components.py
  README.md
```

## Component responsibilities

### Feature-Based Application Layer

The top-level behavior is now organized around features:

- `application/conversation`: answer a user question
- `application/retrieval`: retrieve, rerank, build context, generate answer
- `application/knowledge_ingestion`: run the offline indexing workflow

This is the layer that should keep growing as product behavior expands.

### Ports and Composition

`app/core/ports` defines the application contracts for:

- offline ingestion and persistence
- query processing and retrieval orchestration
- generation providers

`app/bootstrap/composition.py` is the composition root used by the API and
scripts. That keeps dependency construction out of `ChatService`,
`RAGPipeline`, and `VectorRepository`.

### `VectorRepository`

`VectorRepository` is the boundary between offline indexing and online serving.
It:

- embeds incoming queries with the same embedding contract used for indexing
- queries the configured vector store
- rebuilds the offline index if the vector store is empty
- receives its rebuild pipeline from the composition root

This keeps the API stateless and lets us move to a managed vector store later
without changing `ChatService`.

### Vector Store Architecture

Vector storage is package-based and backend-driven, but it is intentionally
owned by the retrieval context rather than the offline ingestion context.

Current package shape:

- `rag/vector_store/base.py`: abstract backend contract
- `rag/vector_store/faiss_store.py`: FAISS implementation
- `rag/vector_store/factory.py`: backend selection and composition
- `rag/vector_store/__init__.py`: stable public exports

To add another backend later, the intended path is:

1. Implement the backend against `BaseVectorStore`
2. Add configuration for that backend
3. Register it in `VectorStoreFactory`

The repository and ingestion pipeline should not need structural changes.

### Hybrid retrieval

The current implementation uses FAISS for dense retrieval and a lightweight
lexical fusion layer in the retriever:

- dense search from FAISS
- sparse lexical boost from keyword overlap in the retriever

This mirrors production hybrid retrieval while keeping the database layer
replaceable. A future Qdrant/Pinecone/Weaviate implementation only needs to
conform to the `BaseVectorStore` contract.

### Chunking

Chunking is now strategy-based and plug-and-play. The offline pipeline builds a
chunker through `ChunkerFactory`, so you can switch implementations through
configuration without changing the ingestion pipeline.

Available chunkers today:

- `tiktoken`: industry-grade tokenizer-backed chunking for realistic model token budgets
- `huggingface`: tokenizer-backed chunking using a local Hugging Face tokenizer
- `word`: lightweight whitespace-token chunking for fallback or low-dependency runs

Relevant settings:

- `CHUNKER_TYPE`
- `CHUNKER_ENCODING_NAME`
- `CHUNKER_HF_MODEL_NAME`
- `CHUNK_SIZE_TOKENS`
- `CHUNK_OVERLAP_TOKENS`

### Cleaning

Cleaning now uses a strategy package and a factory-based selection model.

Available cleaners today:

- `conservative`: low-risk whitespace and control-character normalization
- `aggressive`: strips common markup noise before normalization

Relevant setting:

- `CLEANER_TYPE`

### Embedding

Embedding is also package-based and strategy-driven.

Available embedders today:

- `auto`: prefer sentence-transformers and fall back to hashing
- `sentence_transformer`: explicitly use a sentence-transformer model
- `hashing`: deterministic local fallback with no model download requirement

Relevant settings:

- `EMBEDDER_TYPE`
- `EMBEDDING_MODEL`
- `EMBEDDING_DIMENSIONS`

### Reranking

The reranker is intentionally separated from retrieval so we can switch between
lightweight lexical ranking and semantic cross-encoder ranking without changing
the service layer.

### Providers

Generation providers live in `app/providers`, not `app/rag`, so the RAG
pipeline depends on an abstraction instead of a concrete SDK or hosted vendor.

Current package shape:

- `providers/base.py`: generation contract
- `providers/factory.py`: provider selection
- `providers/ollama_provider.py`: Ollama adapter
- `providers/openai_provider.py`: OpenAI adapter

This keeps provider selection configuration-driven and makes model-vendor
changes independent from retrieval logic.

### Context building

The context builder is responsible for:

- token budgeting
- deduplication
- top-k selection
- final prompt construction

This keeps token overflow and noisy context under control.

## Quickstart

### 1. Install dependencies

```bash
pip install -r requirements.txt
```

### 2. Configure environment

Copy `.env.example` to `.env` and adjust as needed.

If you want Redis-backed caching, start a local Redis instance before running
the API:

```powershell
docker run --rm -p 6379:6379 redis:7-alpine
```

### 3. Build the offline index

```bash
python scripts/rebuild_index.py
```

This scans `DATA_DIR`, chunks documents, generates embeddings, writes vectors to
FAISS, and emits the JSON artifact.

### 4. Start the API

```bash
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

### 5. Open docs

`http://127.0.0.1:8000/docs`

## Configuration

Important settings:

- `DATA_DIR`: source knowledge files
- `SERVICE_NAME`: service identity returned by health checks and OpenAPI
- `SERVICE_VERSION`: service version returned by health checks and OpenAPI
- `LOG_LEVEL`: application log level
- `INDEX_ARTIFACT_PATH`: persisted offline index
- `VECTOR_STORE_TYPE`: active vector-store backend
- `REDIS_CACHE_ENABLED`: enable or disable Redis-backed retrieval caching
- `REDIS_URL`: Redis connection string
- `REDIS_CACHE_NAMESPACE`: cache namespace prefix
- `RETRIEVAL_CACHE_TTL_SECONDS`: TTL for cached retrieval results
- `FAISS_INDEX_PATH`: FAISS binary index location
- `FAISS_METADATA_PATH`: FAISS metadata sidecar
- `LLM_TYPE`: active generation provider (`ollama` or `openai`)
- `OPENAI_API_KEY`: OpenAI API key when using the OpenAI provider
- `OPENAI_BASE_URL`: OpenAI-compatible base URL
- `OPENAI_MODEL`: OpenAI model name
- `CLEANER_TYPE`: cleaner strategy (`conservative` or `aggressive`)
- `EMBEDDER_TYPE`: embedder strategy (`auto`, `sentence_transformer`, or `hashing`)
- `EMBEDDING_MODEL`: preferred embedding model
- `EMBEDDING_DIMENSIONS`: fallback embedding dimensionality
- `EMBEDDING_LOCAL_FILES_ONLY`: when `true`, only use locally cached embedding models and fall back immediately if missing
- `CHUNKER_TYPE`: chunking strategy (`tiktoken` or `word`)
- `CHUNKER_ENCODING_NAME`: tokenizer encoding used by the `tiktoken` chunker
- `CHUNKER_HF_MODEL_NAME`: tokenizer model used by the `huggingface` chunker
- `CHUNK_SIZE_TOKENS`: chunk size
- `CHUNK_OVERLAP_TOKENS`: chunk overlap
- `INGESTION_LOADER_STRATEGY`: `llamaindex`, `hybrid`, or `filesystem`
- `RETRIEVAL_BACKEND`: `llamaindex` or `native`
- `RETRIEVAL_CANDIDATE_K`: number of retrieval candidates before reranking
- `RERANKER_ENABLED`: enable or disable reranking
- `RERANKER_STRATEGY`: `semantic` or `hybrid`
- `RERANKER_MODEL`: semantic reranker model name
- `RERANKER_MAX_CANDIDATES`: maximum candidates scored by the semantic reranker
- `RERANKER_BATCH_SIZE`: cross-encoder batch size
- `RERANKER_TOP_K`: number of chunks kept after reranking
- `GUARDRAIL_ENABLED`: enable or disable request and response guardrails
- `GUARDRAIL_BLOCKED_PATTERNS`: comma-separated prompt-injection patterns
- `GUARDRAIL_OUTPUT_BLOCKED_PATTERNS`: comma-separated leakage patterns
- `GUARDRAIL_REFUSAL_MESSAGE`: refusal message returned when guardrails block a request or response
- `CONTEXT_MAX_CHUNKS`: chunks allowed into the final prompt
- `CONTEXT_MAX_TOKENS`: context token budget

## Testing

Run all tests:

```bash
python -m pytest tests
```

Coverage today includes:

- API chat flow
- offline indexing pipeline
- hybrid retrieval behavior
- reranking
- context building

## Extensibility roadmap

The architecture is set up so we can evolve each layer independently:

- replace the hashing fallback with a production embedding model
- swap the local artifact store for Qdrant/Pinecone/Weaviate
- add BM25 or a dedicated sparse index
- replace the reranker with a cross-encoder
- add corrective filtering or agentic retrieval on top of `RAGPipeline`

## Notes

- The offline artifact directory (`data/.index`) is intentionally excluded from source ingestion.
- The current vector database is FAISS with a metadata sidecar. The architecture is intentionally pluggable so another backend can replace it behind the `BaseVectorStore` contract.
- If `faiss-cpu` is unavailable, the vector store uses a deterministic pure-Python fallback so local development and CI can still run.
- The vector-store package is the official extension point for future database backends and is owned by the retrieval subsystem.
- Retrieval quality will improve most from better chunking, better embeddings, stronger reranking, and better index observability.
- The same embedding contract is used for indexing and querying, which is critical for stable retrieval quality.
