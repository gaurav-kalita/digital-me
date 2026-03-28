# Placeholder for chat request/response schemas
from pydantic import BaseModel
from typing import Any

class ChatRequest(BaseModel):
    question: str

class ChatResponse(BaseModel):
    answer: Any
