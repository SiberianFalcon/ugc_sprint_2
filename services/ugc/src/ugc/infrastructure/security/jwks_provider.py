"""Получение и кеширование ключей JWKS."""

from __future__ import annotations

import asyncio
import time
from collections.abc import Callable
from typing import Any

import httpx
from jwt.algorithms import RSAAlgorithm

from ugc.application.errors import InvalidTokenError
from ugc.infrastructure.settings import AuthSettings


class JwksKeyProvider:
    """Загружает ключи JWKS с TTL и объединением одновременных загрузок."""

    def __init__(
        self,
        settings: AuthSettings,
        now: Callable[[], float] = time.monotonic,
    ) -> None:
        self._settings = settings
        self._now = now
        self._keys: dict[str, Any] = {}
        self._fetched_at: float | None = None
        self._last_attempt: float | None = None
        self._lock = asyncio.Lock()

    async def get_key(self, kid: str) -> Any | None:
        """Возвращает ключ по идентификатору, обновляя кеш по необходимости."""
        if self._has_fresh_key(kid):
            return self._keys[kid]
        await self._refresh(kid)
        return self._keys.get(kid)

    def _has_fresh_key(self, kid: str) -> bool:
        return kid in self._keys and self._is_fresh()

    def _is_fresh(self) -> bool:
        if self._fetched_at is None:
            return False
        return (
            self._now() - self._fetched_at
            < self._settings.jwks_cache_ttl_seconds
        )

    def _can_attempt(self) -> bool:
        if self._last_attempt is None:
            return True
        return (
            self._now() - self._last_attempt
            >= self._settings.jwks_refresh_min_seconds
        )

    async def _refresh(self, kid: str) -> None:
        async with self._lock:
            if self._has_fresh_key(kid):
                return
            if not self._can_attempt():
                return
            self._last_attempt = self._now()
            await self._load()

    async def _load(self) -> None:
        try:
            async with httpx.AsyncClient(
                timeout=self._settings.timeout_seconds
            ) as client:
                response = await client.get(self._settings.jwks_url)
                response.raise_for_status()
                jwks = response.json()
        except (httpx.HTTPError, ValueError) as error:
            raise InvalidTokenError(
                "Не удалось получить ключи проверки токенов."
            ) from error
        self._keys = {
            jwk["kid"]: RSAAlgorithm.from_jwk(jwk)
            for jwk in jwks.get("keys", [])
            if "kid" in jwk
        }
        self._fetched_at = self._now()
