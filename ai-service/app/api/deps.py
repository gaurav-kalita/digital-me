# ai-service2/app/api/deps.py

from typing import Any
from uuid import uuid4

from fastapi import Depends, HTTPException, Request, status

from app.core.config import settings
from app.core.logger import client_ip_context, logger, method_context, path_context, request_id_context
from app.core.security import verify_jwt

async def get_current_user(request: Request) -> Any:
    token = request.headers.get("Authorization")
    if not token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing token")
    return verify_jwt(token)


async def request_logging_middleware(request: Request, call_next):
    import time

    start_time = time.perf_counter()
    request_id = request.headers.get(settings.REQUEST_ID_HEADER) or uuid4().hex
    client_ip = request.client.host if request.client else "-"
    request.state.request_id = request_id

    request_tokens = [
        request_id_context.set(request_id),
        method_context.set(request.method),
        path_context.set(request.url.path),
        client_ip_context.set(client_ip),
    ]

    try:
        with logger.contextualize(
            request_id=request_id,
            method=request.method,
            path=request.url.path,
            client_ip=client_ip,
        ):
            response = await call_next(request)
            duration_ms = (time.perf_counter() - start_time) * 1000
            response.headers[settings.REQUEST_ID_HEADER] = request_id
            logger.bind(
                status_code=response.status_code,
                duration_ms=round(duration_ms, 2),
            ).info("request completed")
            return response
    except Exception:
        duration_ms = (time.perf_counter() - start_time) * 1000
        logger.bind(duration_ms=round(duration_ms, 2)).exception("request failed")
        raise
    finally:
        request_id_context.reset(request_tokens[0])
        method_context.reset(request_tokens[1])
        path_context.reset(request_tokens[2])
        client_ip_context.reset(request_tokens[3])
