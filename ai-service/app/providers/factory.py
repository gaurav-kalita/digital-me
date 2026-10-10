"""Generation provider selection.

This module is an infrastructure adapter. Higher layers should receive already
constructed providers from the composition root instead of importing this
factory directly.
"""

from typing import Optional

from app.core.config import settings
from app.providers.base import BaseLLMProvider
from app.providers.ollama_provider import OllamaProvider
from app.providers.openai_provider import OpenAIProvider


class ProviderFactory:
    """Factory for selecting generation providers from configuration."""

    @staticmethod
    def create(provider_type: Optional[str] = None, **kwargs) -> BaseLLMProvider:
        selected_type = (provider_type or settings.LLM_TYPE).lower()

        if selected_type == "ollama":
            return OllamaProvider(**kwargs)
        if selected_type == "openai":
            return OpenAIProvider(**kwargs)

        raise ValueError("Unsupported LLM provider type: %s" % selected_type)
