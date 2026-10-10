"""OpenAI-backed generation provider."""

import httpx
from tenacity import retry, stop_after_attempt, wait_exponential

from app.core.config import settings
from app.core.logger import logger
from app.providers.base import BaseLLMProvider


class OpenAIProvider(BaseLLMProvider):
    """Remote generation provider backed by the OpenAI Chat Completions API."""

    def __init__(
        self,
        api_key: str = None,
        base_url: str = None,
        model: str = None,
        timeout_seconds: int = 60,
    ):
        self.api_key = api_key or settings.OPENAI_API_KEY or settings.LLM_API_KEY
        self.base_url = (base_url or settings.OPENAI_BASE_URL).rstrip("/")
        self.model = model or settings.OPENAI_MODEL
        self.timeout_seconds = timeout_seconds

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=5),
    )
    async def generate(self, prompt: str) -> str:
        if not self.api_key:
            raise ValueError("OPENAI_API_KEY or LLM_API_KEY is required for the openai provider")

        try:
            async with httpx.AsyncClient(timeout=self.timeout_seconds) as client:
                response = await client.post(
                    "%s/chat/completions" % self.base_url,
                    headers={"Authorization": "Bearer %s" % self.api_key},
                    json={
                        "model": self.model,
                        "messages": [
                            {
                                "role": "system",
                                "content": "Answer only from the supplied context. If the answer is missing, say you do not know.",
                            },
                            {"role": "user", "content": prompt},
                        ],
                        "temperature": 0.1,
                    },
                )
                response.raise_for_status()
                payload = response.json()
                choices = payload.get("choices", [])
                if not choices:
                    raise ValueError("OpenAI provider returned no choices")

                message = choices[0].get("message", {})
                return str(message.get("content", "")).strip()
        except Exception as exc:
            logger.bind(provider="openai", model=self.model, base_url=self.base_url).opt(exception=exc).error(
                "OpenAI provider call failed"
            )
            raise
