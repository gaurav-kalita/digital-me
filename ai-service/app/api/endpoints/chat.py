from functools import lru_cache

from fastapi import APIRouter, Depends

from app.models.chat import ChatRequest, ChatResponse
from app.services.chat_service import ChatService

router = APIRouter()

@lru_cache(maxsize=1)
def get_chat_service() -> ChatService:
    return ChatService()


@router.post("/", response_model=ChatResponse)
async def chat_endpoint(
    req: ChatRequest,
    chat_service: ChatService = Depends(get_chat_service),
):
    return await chat_service.chat(req.question, user=None)
