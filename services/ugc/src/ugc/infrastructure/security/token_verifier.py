"""Проверка JWT-токенов по JWKS."""

from typing import Any

import httpx
import jwt
from jwt.algorithms import RSAAlgorithm

from ugc.application.errors import InvalidTokenError
from ugc.domain.content.user_id import UserId
from ugc.infrastructure.settings import AuthSettings


class JwtTokenVerifier:
    """Проверяет RS256 JWT и извлекает идентификатор пользователя."""

    def __init__(self, settings: AuthSettings) -> None:
        self._settings = settings
        self._keys: dict[str, Any] = {}

    async def verify(self, token: str) -> UserId:
        """Проверяет токен и возвращает идентификатор пользователя."""
        if not self._settings.jwks_url:
            raise InvalidTokenError("Проверка токенов не настроена.")
        try:
            header = jwt.get_unverified_header(token)
        except jwt.PyJWTError as error:
            raise InvalidTokenError("Недействительный токен.") from error
        kid = header.get("kid")
        if not isinstance(kid, str):
            raise InvalidTokenError("Токен не содержит идентификатор ключа.")
        key = await self._key_for(kid)
        try:
            payload = jwt.decode(
                token,
                key=key,
                algorithms=["RS256"],
                issuer=self._settings.issuer,
            )
        except jwt.PyJWTError as error:
            raise InvalidTokenError("Недействительный токен.") from error
        subject = payload.get("sub")
        if not isinstance(subject, str) or not subject:
            raise InvalidTokenError(
                "Токен не содержит идентификатор пользователя."
            )
        return UserId(subject)

    async def _key_for(self, kid: str) -> Any:
        if kid not in self._keys:
            await self._fetch_keys()
        if kid not in self._keys:
            raise InvalidTokenError("Ключ подписи токена не найден.")
        return self._keys[kid]

    async def _fetch_keys(self) -> None:
        async with httpx.AsyncClient(
            timeout=self._settings.timeout_seconds
        ) as client:
            response = await client.get(self._settings.jwks_url)
            response.raise_for_status()
            jwks = response.json()
        self._keys = {
            jwk["kid"]: RSAAlgorithm.from_jwk(jwk)
            for jwk in jwks.get("keys", [])
            if "kid" in jwk
        }
