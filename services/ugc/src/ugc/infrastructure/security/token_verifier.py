"""Проверка JWT-токенов по JWKS."""

import jwt

from ugc.application.errors import InvalidTokenError
from ugc.domain.content.user_id import UserId
from ugc.infrastructure.security.jwks_provider import JwksKeyProvider
from ugc.infrastructure.settings import AuthSettings


class JwtTokenVerifier:
    """Проверяет RS256 JWT и извлекает идентификатор пользователя."""

    def __init__(self, settings: AuthSettings) -> None:
        self._settings = settings
        self._key_provider = JwksKeyProvider(settings)

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
        key = await self._key_provider.get_key(kid)
        if key is None:
            raise InvalidTokenError("Ключ подписи токена не найден.")
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
