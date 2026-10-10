"""Redis-backed cache adapter with a safe no-op fallback."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from app.core.logger import logger
from app.core.ports.cache import CacheStore


class NullCacheStore(CacheStore):
    """Fallback cache implementation used when Redis is unavailable."""

    async def get(self, key: str) -> Optional[str]:
        del key
        return None

    async def set(self, key: str, value: str, ttl_seconds: int) -> None:
        del key, value, ttl_seconds

    async def delete(self, key: str) -> None:
        del key

    async def close(self) -> None:
        return None

    def diagnostics(self) -> dict:
        return {
            "enabled": False,
            "available": True,
            "backend": "null",
            "disabled_reason": None,
        }


@dataclass
class RedisCacheStore(CacheStore):
    """Async Redis cache adapter.

    The adapter degrades gracefully when the Redis package is missing or the
    connection cannot be established. That keeps the application runnable in
    local environments while still enabling Redis-backed caching when available.
    """

    url: str
    namespace: str
    required: bool = False

    def __post_init__(self) -> None:
        self._client = None
        self._disabled_reason = ""
        self._initialize_client()

    def _initialize_client(self) -> None:
        try:
            from redis.asyncio import Redis
        except Exception as exc:  # pragma: no cover - import availability guard
            self._disabled_reason = "redis package is not installed"
            self._client = None
            if self.required:
                raise RuntimeError(self._disabled_reason) from exc
            logger.warning("Redis cache disabled", extra={"reason": self._disabled_reason})
            return

        try:
            self._client = Redis.from_url(
                self.url,
                socket_connect_timeout=2,
                socket_timeout=2,
                decode_responses=True,
            )
        except Exception as exc:
            self._disabled_reason = str(exc)
            self._client = None
            if self.required:
                raise RuntimeError(f"Failed to initialize Redis client: {exc}") from exc
            logger.warning("Redis cache disabled", extra={"reason": self._disabled_reason})

    def _namespaced(self, key: str) -> str:
        return f"{self.namespace}:{key}"

    async def get(self, key: str) -> Optional[str]:
        if self._client is None:
            return None

        try:
            return await self._client.get(self._namespaced(key))
        except Exception as exc:
            logger.warning("Redis cache read failed", extra={"key": key, "error": str(exc)})
            return None

    async def set(self, key: str, value: str, ttl_seconds: int) -> None:
        if self._client is None:
            return

        try:
            await self._client.set(self._namespaced(key), value, ex=ttl_seconds)
        except Exception as exc:
            logger.warning("Redis cache write failed", extra={"key": key, "error": str(exc)})

    async def delete(self, key: str) -> None:
        if self._client is None:
            return

        try:
            await self._client.delete(self._namespaced(key))
        except Exception as exc:
            logger.warning("Redis cache delete failed", extra={"key": key, "error": str(exc)})

    async def close(self) -> None:
        if self._client is None:
            return

        try:
            await self._client.aclose()
        except Exception as exc:
            logger.warning("Redis cache close failed", extra={"error": str(exc)})

    def diagnostics(self) -> dict:
        return {
            "enabled": True,
            "available": self._client is not None,
            "backend": "redis",
            "url": self.url,
            "disabled_reason": self._disabled_reason or None,
        }
