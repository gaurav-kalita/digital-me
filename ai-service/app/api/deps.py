from fastapi import Depends, Request
from app.core.security import verify_jwt
from fastapi import HTTPException, status
from typing import Any

async def get_current_user(request: Request) -> Any:
    token = request.headers.get("Authorization")
    if not token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing token")
    return verify_jwt(token)

async def request_logging_middleware(request: Request, call_next):
    from app.core.logger import logger
    import time
    start_time = time.time()
    response = await call_next(request)
    duration = time.time() - start_time
    logger.info(f"{request.method} {request.url.path} completed in {duration:.3f}s")
    return response
