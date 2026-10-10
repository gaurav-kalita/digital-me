"""Port definitions for caching infrastructure."""

from typing import Optional, Protocol


class CacheStore(Protocol):
    """Async cache contract used by application and repository layers."""

    async def get(self, key: str) -> Optional[str]:
        ...

    async def set(self, key: str, value: str, ttl_seconds: int) -> None:
        ...

    async def delete(self, key: str) -> None:
        ...
