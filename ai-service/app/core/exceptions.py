from fastapi import Request, FastAPI
from fastapi.responses import JSONResponse
from loguru import logger

class AIServiceError(Exception):
    pass

def add_exception_handlers(app: FastAPI):
    @app.exception_handler(AIServiceError)
    async def ai_service_error_handler(request: Request, exc: AIServiceError):
        logger.error(f"AIServiceError: {exc}")
        return JSONResponse(status_code=500, content={"detail": str(exc)})

    @app.exception_handler(Exception)
    async def generic_exception_handler(request: Request, exc: Exception):
        logger.error(f"Unhandled error: {exc}")
        return JSONResponse(status_code=500, content={"detail": "Internal server error"})