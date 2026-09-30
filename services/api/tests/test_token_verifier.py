"""Тесты проверки JWT-токенов."""

import base64
from typing import ClassVar

import jwt
import pytest
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives.asymmetric.rsa import (
    RSAPrivateKey,
    RSAPublicKey,
)

from api.application.errors import InvalidTokenError
from api.domain.event.user_id import UserId
from api.infrastructure.security.token_verifier import JwtTokenVerifier
from api.infrastructure.settings import AuthSettings


def _b64url(value: int) -> str:
    raw = value.to_bytes((value.bit_length() + 7) // 8, "big")
    return base64.urlsafe_b64encode(raw).rstrip(b"=").decode()


def _jwks(
    public_key: RSAPublicKey, kid: str = "test-kid"
) -> dict[str, object]:
    numbers = public_key.public_numbers()
    return {
        "keys": [
            {
                "kty": "RSA",
                "kid": kid,
                "use": "sig",
                "alg": "RS256",
                "n": _b64url(numbers.n),
                "e": _b64url(numbers.e),
            }
        ]
    }


class _FakeResponse:
    def __init__(self, payload: object) -> None:
        self._payload = payload

    def raise_for_status(self) -> None:
        return None

    def json(self) -> object:
        return self._payload


class _FakeClient:
    response: ClassVar[object | None] = None

    def __init__(self, **kwargs: object) -> None:
        return None

    async def __aenter__(self) -> "_FakeClient":
        return self

    async def __aexit__(self, *args: object) -> None:
        return None

    async def get(self, url: str) -> object:
        return _FakeClient.response


def _install_fake(
    monkeypatch: pytest.MonkeyPatch, jwks: dict[str, object]
) -> None:
    _FakeClient.response = _FakeResponse(jwks)
    monkeypatch.setattr(
        "api.infrastructure.security.token_verifier.httpx.AsyncClient",
        _FakeClient,
    )


def _settings() -> AuthSettings:
    return AuthSettings(jwks_url="https://auth/jwks", issuer="auth-service")


async def test_verify_returns_user_id(monkeypatch: pytest.MonkeyPatch) -> None:
    """Валидный токен даёт идентификатор пользователя."""
    private_key = _private_key()
    _install_fake(monkeypatch, _jwks(private_key.public_key()))
    token = jwt.encode(
        {"sub": "user-1", "iss": "auth-service"},
        private_key,
        algorithm="RS256",
        headers={"kid": "test-kid"},
    )

    result = await JwtTokenVerifier(_settings()).verify(token)

    assert result == UserId("user-1")


async def test_verify_rejects_garbage_token(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Некорректный токен отклоняется."""
    private_key = _private_key()
    _install_fake(monkeypatch, _jwks(private_key.public_key()))

    with pytest.raises(InvalidTokenError):
        await JwtTokenVerifier(_settings()).verify("not-a-token")


async def test_verify_rejects_token_without_subject(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Токен без subject отклоняется."""
    private_key = _private_key()
    _install_fake(monkeypatch, _jwks(private_key.public_key()))
    token = jwt.encode(
        {"iss": "auth-service"},
        private_key,
        algorithm="RS256",
        headers={"kid": "test-kid"},
    )

    with pytest.raises(InvalidTokenError):
        await JwtTokenVerifier(_settings()).verify(token)


def _private_key() -> RSAPrivateKey:
    return rsa.generate_private_key(public_exponent=65537, key_size=2048)
