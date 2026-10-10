# ai-service2/app/core/logger.py

import sys
from contextvars import ContextVar

from loguru import logger as _logger

from app.core.config import settings


request_id_context: ContextVar[str] = ContextVar("request_id", default="-")
method_context: ContextVar[str] = ContextVar("method", default="-")
path_context: ContextVar[str] = ContextVar("path", default="-")
client_ip_context: ContextVar[str] = ContextVar("client_ip", default="-")


def _patch_record(record):
    record["extra"].setdefault("service", settings.SERVICE_NAME)
    record["extra"].setdefault("request_id", request_id_context.get())
    record["extra"].setdefault("method", method_context.get())
    record["extra"].setdefault("path", path_context.get())
    record["extra"].setdefault("client_ip", client_ip_context.get())
    return record


logger = _logger.patch(_patch_record)


def setup_logging() -> None:
    logger.remove()
    logger.configure(extra={"service": settings.SERVICE_NAME})
    logger.add(
        sys.stdout,
        level=settings.LOG_LEVEL.upper(),
        format=(
            "<green>{time:YYYY-MM-DDTHH:mm:ss.SSSZZ}</green> "
            "<level>{level:<8}</level> "
            "<cyan>{extra[service]}</cyan> "
            "<magenta>{extra[request_id]}</magenta> "
            "<blue>{extra[method]}</blue> "
            "<blue>{extra[path]}</blue> "
            "<yellow>{extra[client_ip]}</yellow> "
            "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - "
            "<level>{message}</level>"
        ),
        backtrace=True,
        diagnose=False,
    )
    logger.info(
        "Logging configured",
        extra={
            "log_level": settings.LOG_LEVEL.upper(),
        },
    )

