# Digital Me AI Service

## Overview

This service now follows a two-stage RAG architecture:

1. Offline pipeline for ingestion, cleaning, chunking, embedding, and artifact generation
2. Online pipeline for query processing, retrieval, reranking, context building, and generation

The goal is to keep ingestion concerns separate from serving concerns so we can
scale retrieval quality without rewriting the API layer.

## Architecture

### Offline pipeline

The offline pipeline lives in `app/data_layer` and runs:

`raw files -> normalization -> chunking -> embedding -> persisted index artifact`

Key modules:

- `filesystem.py`: loads `.txt`, `.md`, and `.json` source documents from `DATA_DIR`
- `cleaner/`: pluggable document cleaning strategies
- `chunker.py`: token-aware overlapping chunking
  supports pluggable strategies selected from configuration
- `embedder/`: pluggable embedding strategies with deterministic fallback
- `pipeline.py`: offline processor that writes indexed chunk artifacts
- `index.py`: hybrid search implementation used by the online layer
- `vector_store/`: pluggable vector database backends and selection factory

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

- `pipeline.py`: orchestrates the online RAG flow
- `retriever.py`: executes search across one or more query variants
- `reranker.py`: improves precision over retriever candidates
- `contextBuilder.py`: builds a token-budgeted prompt
- `llm_client.py`: generation provider abstraction

The API entrypoint calls `ChatService`, which delegates to the RAG pipeline and
then the LLM.

## Folder structure

```text
ai-service/
  app/
    api/
      deps.py
      endpoints/
        chat.py
        health.py
    core/
      config.py
      exceptions.py
      logger.py
      security.py
    data_layer/
      cleaner.py
      chunker.py
      embedder.py
      filesystem.py
      index.py
      interfaces.py
      models.py
      pipeline.py
    models/
      chat.py
      user.py
    rag/
      contextBuilder.py
      llm_client.py
      pipeline.py
      reranker.py
      retriever.py
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

### `VectorRepository`

`VectorRepository` is the boundary between offline indexing and online serving.
It:

- embeds incoming queries with the same embedding contract used for indexing
- queries the configured vector store
- rebuilds the offline index if the vector store is empty

This keeps the API stateless and lets us move to a managed vector store later
without changing `ChatService`.

### Vector Store Architecture

Vector storage is now package-based and backend-driven, matching the cleaner,
chunker, and embedder architecture.

Current package shape:

- `vector_store/base.py`: abstract backend contract
- `vector_store/faiss_store.py`: FAISS implementation
- `vector_store/factory.py`: backend selection and composition
- `vector_store/__init__.py`: stable public exports

To add another backend later, the intended path is:

1. Implement the backend against `BaseVectorStore`
2. Add configuration for that backend
3. Register it in `VectorStoreFactory`

The repository and ingestion pipeline should not need any structural changes.

### Hybrid retrieval

The current implementation uses FAISS for dense retrieval and a lightweight
lexical fusion layer in the retriever:

- dense search from FAISS
- sparse lexical boost from keyword overlap in the retriever

This mirrors production hybrid retrieval while keeping the database layer
replaceable. A future Qdrant/Pinecone/Weaviate implementation only needs to
conform to the `VectorStore` protocol.

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

The reranker is intentionally separated from retrieval so we can replace the
current lightweight reranker with a cross-encoder or LLM reranker later.

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

### 3. Build the offline index

```bash
python scripts/rebuild_index.py
```

This scans `DATA_DIR`, chunks documents, generates embeddings, writes vectors to
FAISS, and emits the JSON artifact.

### 4. Start the API

```bash
uvicorn app.main:app --reload
```

### 5. Open docs

`http://localhost:8000/docs`

## Configuration

Important settings:

- `DATA_DIR`: source knowledge files
- `INDEX_ARTIFACT_PATH`: persisted offline index
- `VECTOR_STORE_TYPE`: active vector-store backend
- `FAISS_INDEX_PATH`: FAISS binary index location
- `FAISS_METADATA_PATH`: FAISS metadata sidecar
- `CLEANER_TYPE`: cleaner strategy (`conservative` or `aggressive`)
- `EMBEDDER_TYPE`: embedder strategy (`auto`, `sentence_transformer`, or `hashing`)
- `EMBEDDING_MODEL`: preferred embedding model
- `EMBEDDING_DIMENSIONS`: fallback embedding dimensionality
- `CHUNKER_TYPE`: chunking strategy (`tiktoken` or `word`)
- `CHUNKER_ENCODING_NAME`: tokenizer encoding used by the `tiktoken` chunker
- `CHUNKER_HF_MODEL_NAME`: tokenizer model used by the `huggingface` chunker
- `CHUNK_SIZE_TOKENS`: chunk size
- `CHUNK_OVERLAP_TOKENS`: chunk overlap
- `RETRIEVAL_CANDIDATE_K`: number of retrieval candidates before reranking
- `RERANKER_TOP_K`: number of chunks kept after reranking
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
- The current vector database is FAISS with a metadata sidecar. The architecture is intentionally pluggable so another backend can replace it behind the `VectorStore` protocol.
- The vector-store package is the official extension point for future database backends.
- Retrieval quality will improve most from better chunking, better embeddings, and stronger reranking.
- The same embedding contract is used for indexing and querying, which is critical for stable retrieval quality.
