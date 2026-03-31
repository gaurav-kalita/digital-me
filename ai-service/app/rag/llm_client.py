"""LLM clients used by the generation layer."""

from abc import ABC, abstractmethod

import httpx
from tenacity import retry, stop_after_attempt, wait_exponential

from app.core.config import settings
from app.core.logger import logger


class BaseLLMClient(ABC):
    """Abstract contract for generation providers."""

    @abstractmethod
    async def generate(self, prompt: str) -> str:
        ...


class OllamaLLMClient(BaseLLMClient):
    """Local generation provider backed by Ollama."""

    def __init__(self, ollama_url: str = None, model: str = None, timeout_seconds: int = 60):
        self.ollama_url = ollama_url or settings.OLLAMA_URL
        self.model = model or settings.OLLAMA_MODEL
        self.timeout_seconds = timeout_seconds

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=5),
    )
    async def generate(self, prompt: str) -> str:
        try:
            async with httpx.AsyncClient(timeout=self.timeout_seconds) as client:
                response = await client.post(
                    "%s/api/generate" % self.ollama_url,
                    json={
                        "model": self.model,
                        "prompt": prompt,
                        "stream": False,
                    },
                )
                response.raise_for_status()
                payload = response.json()
                return (payload.get("response") or "").strip()
        except Exception:
            logger.error("Ollama LLM call failed", exc_info=True)
            raise


class LLMClientFactory:
    """Factory that keeps provider selection in one place."""

    @staticmethod
    def get_client(llm_type: str = None, **kwargs) -> BaseLLMClient:
        selected_type = llm_type or settings.LLM_TYPE
        if selected_type == "ollama":
            return OllamaLLMClient(**kwargs)
        raise ValueError("Unsupported LLM type: %s" % selected_type)


LLMClient = LLMClientFactory.get_client
