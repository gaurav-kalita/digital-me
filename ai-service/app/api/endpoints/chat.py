from fastapi import APIRouter
from app.services.chat_service import ChatService
from pydantic import BaseModel
from typing import Any

router = APIRouter()

class ChatRequest(BaseModel):
    question: str

@router.post("/", response_model=Any)
async def chat_endpoint(
    req: ChatRequest,
    chat_service: ChatService = ChatService()
):
    return await chat_service.chat(req.question, user=None)
