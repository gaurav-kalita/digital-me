"""Aggressive text normalization strategy."""

import re

from app.data_layer.cleaner.base import BaseCleaner


class AggressiveCleaner(BaseCleaner):
    """Cleaner that removes common markup noise before whitespace normalization."""

    def clean(self, text: str) -> str:
        # Replace null-byte characters with spaces.
        cleaned = text.replace("\x00", " ")
        # Remove HTML/XML tags like <div> or <p>.
        cleaned = re.sub(r"<[^>]+>", " ", cleaned)
        # Remove Markdown links like [text](url).
        cleaned = re.sub(r"\[[^\]]+\]\([^)]+\)", " ", cleaned)
        # Collapse multiple spaces or tabs into one space.
        cleaned = re.sub(r"[ \t]+", " ", cleaned)
        # Collapse multiple newlines into a single newline.
        cleaned = re.sub(r"\n{2,}", "\n", cleaned)
        # Collapse all remaining whitespace into a single space.
        cleaned = re.sub(r"\s+", " ", cleaned)
        # Remove leading and trailing whitespace.
        return cleaned.strip()
