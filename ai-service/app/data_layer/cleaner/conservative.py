"""Conservative text normalization strategy."""

import re

from app.data_layer.cleaner.base import BaseCleaner


class ConservativeCleaner(BaseCleaner):
    """Applies low-risk normalization without aggressively rewriting content."""

    def clean(self, text: str) -> str:
        # Replace null-byte characters with spaces.
        cleaned = text.replace("\x00", " ")

        # Replace consecutive whitespace characters with a single space.
        cleaned = re.sub(r"\s+", " ", cleaned)

        # Remove leading and trailing whitespace.
        return cleaned.strip()
