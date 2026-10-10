# ai-service2/app/main.py

from contextlib import asynccontextmanager

from fastapi import FastAPI
from app.api.endpoints import chat, forms, health
from app.bootstrap.composition import build_cache_store
from app.core.config import settings
from app.core.logger import logger, setup_logging
from app.core.runtime import build_runtime_status
from app.core.exceptions import add_exception_handlers
from app.api.deps import request_logging_middleware

setup_logging()


@asynccontextmanager
async def lifespan(app: FastAPI):
    del app
    runtime_status = build_runtime_status()
    startup_context = {
        "service": settings.SERVICE_NAME,
        "version": settings.SERVICE_VERSION,
        "llm_type": settings.LLM_TYPE,
        "ollama_url": settings.OLLAMA_URL,
        "ollama_model": settings.OLLAMA_MODEL,
        "vector_store": settings.VECTOR_STORE_TYPE,
        "retrieval_backend": settings.retrieval.backend,
        "guardrails_enabled": settings.guardrails.enabled,
        "cache_enabled": settings.cache.enabled,
    }

    if runtime_status.ready:
        logger.bind(status=runtime_status.status, ready=runtime_status.ready, **startup_context).info(
            "application started"
        )
    else:
        logger.bind(status=runtime_status.status, ready=runtime_status.ready, **startup_context).warning(
            "application started in degraded mode"
        )

    yield
    cache_store = build_cache_store()
    close = getattr(cache_store, "close", None)
    if close is not None:
        await close()


app = FastAPI(
    title=settings.SERVICE_NAME,
    version=settings.SERVICE_VERSION,
    lifespan=lifespan,
)

# Middleware
app.middleware('http')(request_logging_middleware)

# Routers
app.include_router(chat.router, prefix="/chat", tags=["chat"])
app.include_router(forms.router, prefix="/forms", tags=["forms"])
app.include_router(health.router, prefix="/health", tags=["health"])

# Exception handlers
add_exception_handlers(app)
