from typing import List
from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    question: str = Field(..., min_length=3, max_length=512)


class ChatResponse(BaseModel):
    answer: str
    sources: List[str] = Field(default_factory=list)
    query: str
