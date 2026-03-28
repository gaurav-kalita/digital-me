from abc import ABC, abstractmethod
import asyncio
from tenacity import retry, stop_after_attempt, wait_exponential
import httpx
from app.core.config import settings
from app.core.logger import logger

class BaseLLMClient(ABC):
    @abstractmethod
    async def generate(self, prompt: str) -> str:
        pass

class OllamaLLMClient(BaseLLMClient):
    def __init__(self, ollama_url: str = None, model: str = None):
        self.ollama_url = ollama_url or getattr(settings, "OLLAMA_URL", "http://localhost:11434")
        self.model = model or getattr(settings, "OLLAMA_MODEL", "gemma:3b")

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=5),
    )
    async def generate(self, prompt: str) -> str:
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.ollama_url}/api/generate",
                    json={
                        "model": self.model,
                        "prompt": prompt,
                        "stream": False
                    },
                    timeout=60
                )
                response.raise_for_status()
                data = response.json()
                return data.get("response") or data.get("message", "")
        except Exception as e:
            logger.error("Ollama LLM call failed, retrying...", exc_info=True)
            raise e

# Example: add more LLM clients by subclassing BaseLLMClient
# class OpenAILLMClient(BaseLLMClient): ...

# Factory for plug-and-play
class LLMClientFactory:
    @staticmethod
    def get_client(llm_type: str = None, **kwargs) -> BaseLLMClient:
        llm_type = llm_type or getattr(settings, "LLM_TYPE", "ollama")
        if llm_type == "ollama":
            return OllamaLLMClient(**kwargs)
        # elif llm_type == "openai":
        #     return OpenAILLMClient(**kwargs)
        raise ValueError(f"Unsupported LLM type: {llm_type}")

# Default for DI
LLMClient = LLMClientFactory.get_client