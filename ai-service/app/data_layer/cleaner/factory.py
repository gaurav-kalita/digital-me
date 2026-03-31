"""Cleaner factory and selection policy."""

from typing import Optional

from app.core.config import settings
from app.data_layer.cleaner.aggressive import AggressiveCleaner
from app.data_layer.cleaner.base import BaseCleaner
from app.data_layer.cleaner.conservative import ConservativeCleaner


class CleanerFactory:
    """Factory for selecting a cleaner strategy from configuration."""

    @staticmethod
    def create(cleaner_type: Optional[str] = None) -> BaseCleaner:
        selected_type = (cleaner_type or settings.cleaning.strategy).lower()

        if selected_type in {"conservative", "basic", "default"}:
            return ConservativeCleaner()

        if selected_type in {"aggressive", "html"}:
            return AggressiveCleaner()

        raise ValueError("Unsupported cleaner type: %s" % selected_type)
