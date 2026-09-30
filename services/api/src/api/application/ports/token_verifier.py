"""Порт проверки токенов доступа."""

from typing import Protocol

from api.domain.event.user_id import UserId


class TokenVerifier(Protocol):
    """Проверяет токен и возвращает идентификатор пользователя."""

    async def verify(self, token: str) -> UserId:
        """Проверяет токен доступа и возвращает пользователя."""
        ...
