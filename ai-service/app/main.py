# main.py

from fastapi import FastAPI
from app.api.endpoints import chat, health
from app.core.logger import setup_logging
from app.core.exceptions import add_exception_handlers
from app.api.deps import request_logging_middleware

setup_logging()

app = FastAPI()

# Middleware
app.middleware('http')(request_logging_middleware)

# Routers
app.include_router(chat.router, prefix="/chat", tags=["chat"])
app.include_router(health.router, prefix="/health", tags=["health"])

# Exception handlers
add_exception_handlers(app)