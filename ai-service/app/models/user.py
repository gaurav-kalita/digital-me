from pydantic import BaseModel
from typing import Optional

class User(BaseModel):
    id: str
    username: str
    email: Optional[str]

class ChatRequest(BaseModel):
    question: str
