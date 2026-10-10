"""Ollama-backed generation provider."""

import httpx
from tenacity import retry, stop_after_attempt, wait_exponential

from app.core.config import settings
from app.core.logger import logger
from app.providers.base import BaseLLMProvider


class OllamaProvider(BaseLLMProvider):
    """Local generation provider backed by Ollama."""

    def __init__(self, ollama_url: str = None, model: str = None, timeout_seconds: int = 440):
        self.ollama_url = ollama_url or settings.OLLAMA_URL
        self.model = model or settings.OLLAMA_MODEL
        self.timeout_seconds = timeout_seconds

    # @retry(
    #     stop=stop_after_attempt(3),
    #     wait=wait_exponential(multiplier=1, min=1, max=5),
    # )
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
        except Exception as exc:
            logger.bind(
                provider="ollama",
                model=self.model,
                ollama_url=self.ollama_url,
                timeout_seconds=self.timeout_seconds,
                exception_type=type(exc).__name__,
            ).opt(exception=exc).warning("Ollama provider call failed")
            raise
