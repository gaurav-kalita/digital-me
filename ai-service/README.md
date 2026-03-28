# Digital Me AI Service

## Overview

A modular, production-grade AI backend using FastAPI, Clean Architecture, and RAG pipeline.

### Features

- **Chat API**: Secure, JWT-authenticated endpoint for AI chat
- **RAG Pipeline**: Query enhancement, document retrieval, prompt building, LLM response
- **LLM Client**: With retry (exponential backoff)
- **Structured Logging**: Using loguru
- **Request Logging Middleware**
- **Custom Error Handling**
- **Health Endpoint**
- **Vector Store Abstraction**: Placeholder for FAISS/DB
- **Async, Type Hints, SOLID, Dependency Injection**

## Folder Structure

```
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
    models/
      user.py
      chat.py
    rag/
      llm_client.py
      pipeline.py
      vector_store.py
    repositories/
      vector_repository.py
    services/
      chat_service.py
    main.py
  tests/
    test_chat.py
  requirements.txt
  README.md
```

## Quickstart

1. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
2. Set environment variables (see `.env.example`)
3. Run the app:
   ```bash
   uvicorn app.main:app --reload
   ```
4. API docs: http://localhost:8000/docs

## Testing

```bash
pytest
```

## Environment Variables

- `SECRET_KEY` (JWT)
- `LLM_API_KEY`
- `VECTOR_DB_URL`
- ...

## Notes

- Replace vector store placeholder with FAISS/DB as needed.
- Extend models/services for your use case.
