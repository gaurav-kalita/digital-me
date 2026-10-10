from fastapi import Request, FastAPI
from fastapi.responses import JSONResponse

from app.core.logger import logger

class AIServiceError(Exception):
    pass


class GuardrailViolation(Exception):
    pass

def add_exception_handlers(app: FastAPI):
    @app.exception_handler(AIServiceError)
    async def ai_service_error_handler(request: Request, exc: AIServiceError):
        request_id = getattr(request.state, "request_id", "-")
        logger.bind(
            request_id=request_id,
            method=request.method,
            path=request.url.path,
        ).opt(exception=exc).error("AIServiceError")
        return JSONResponse(status_code=500, content={"detail": str(exc), "request_id": request_id})

    @app.exception_handler(GuardrailViolation)
    async def guardrail_violation_handler(request: Request, exc: GuardrailViolation):
        request_id = getattr(request.state, "request_id", "-")
        logger.bind(
            request_id=request_id,
            method=request.method,
            path=request.url.path,
        ).warning("GuardrailViolation: {}", exc)
        return JSONResponse(status_code=400, content={"detail": str(exc), "request_id": request_id})

    @app.exception_handler(Exception)
    async def generic_exception_handler(request: Request, exc: Exception):
        request_id = getattr(request.state, "request_id", "-")
        logger.bind(
            request_id=request_id,
            method=request.method,
            path=request.url.path,
        ).opt(exception=exc).error("Unhandled error")
        return JSONResponse(
            status_code=500,
            content={"detail": "Internal server error", "request_id": request_id},
        )
