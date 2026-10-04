"""Тесты кеша ключей JWKS."""

import asyncio
import base64
from typing import ClassVar

import httpx
import pytest
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives.asymmetric.rsa import (
    RSAPrivateKey,
    RSAPublicKey,
)

from ugc.application.errors import InvalidTokenError
from ugc.infrastructure.security.jwks_provider import JwksKeyProvider
from ugc.infrastructure.settings import AuthSettings


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


def _private_key() -> RSAPrivateKey:
    return rsa.generate_private_key(public_exponent=65537, key_size=2048)


class _Clock:
    """Управляемые монотонные часы."""

    def __init__(self) -> None:
        self.value = 0.0

    def __call__(self) -> float:
        return self.value

    def advance(self, seconds: float) -> None:
        self.value += seconds


class _FakeResponse:
    def __init__(self, payload: object) -> None:
        self._payload = payload

    def raise_for_status(self) -> None:
        return None

    def json(self) -> object:
        return self._payload


class _FakeClient:
    response: ClassVar[object | None] = None
    calls: ClassVar[int] = 0
    fail: ClassVar[bool] = False

    def __init__(self, **kwargs: object) -> None:
        return None

    async def __aenter__(self) -> "_FakeClient":
        return self

    async def __aexit__(self, *args: object) -> None:
        return None

    async def get(self, url: str) -> object:
        type(self).calls += 1
        await asyncio.sleep(0)
        if type(self).fail:
            raise httpx.ConnectError("boom")
        return _FakeClient.response


def _install_fake(
    monkeypatch: pytest.MonkeyPatch, jwks: dict[str, object]
) -> None:
    _FakeClient.response = _FakeResponse(jwks)
    _FakeClient.calls = 0
    _FakeClient.fail = False
    monkeypatch.setattr(
        "ugc.infrastructure.security.jwks_provider.httpx.AsyncClient",
        _FakeClient,
    )


def _settings() -> AuthSettings:
    return AuthSettings(
        jwks_url="https://auth/jwks",
        issuer="auth-service",
        jwks_cache_ttl_seconds=100.0,
        jwks_refresh_min_seconds=10.0,
    )


async def test_key_is_cached_until_ttl(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Ключ берётся из кеша, пока не истёк TTL."""
    _install_fake(monkeypatch, _jwks(_private_key().public_key()))
    clock = _Clock()
    provider = JwksKeyProvider(_settings(), now=clock)

    assert await provider.get_key("test-kid") is not None
    assert await provider.get_key("test-kid") is not None
    assert _FakeClient.calls == 1

    clock.advance(101)
    assert await provider.get_key("test-kid") is not None
    assert _FakeClient.calls == 2


async def test_unknown_kid_refresh_is_rate_limited(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Неизвестный kid не вызывает загрузку чаще минимального интервала."""
    _install_fake(monkeypatch, _jwks(_private_key().public_key()))
    clock = _Clock()
    provider = JwksKeyProvider(_settings(), now=clock)

    assert await provider.get_key("missing") is None
    assert _FakeClient.calls == 1

    assert await provider.get_key("missing") is None
    assert _FakeClient.calls == 1

    clock.advance(11)
    assert await provider.get_key("missing") is None
    assert _FakeClient.calls == 2


async def test_concurrent_loads_are_coalesced(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Одновременные запросы выполняют только одну загрузку ключей."""
    _install_fake(monkeypatch, _jwks(_private_key().public_key()))
    provider = JwksKeyProvider(_settings())

    results = await asyncio.gather(
        *[provider.get_key("test-kid") for _ in range(10)]
    )

    assert all(result is not None for result in results)
    assert _FakeClient.calls == 1


async def test_load_error_becomes_invalid_token(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Ошибка загрузки JWKS превращается в InvalidTokenError."""
    _install_fake(monkeypatch, _jwks(_private_key().public_key()))
    _FakeClient.fail = True
    provider = JwksKeyProvider(_settings())

    with pytest.raises(InvalidTokenError):
        await provider.get_key("test-kid")
