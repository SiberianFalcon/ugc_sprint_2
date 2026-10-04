"""Тесты HTTP-эндпоинтов сервиса контента."""

from collections.abc import Iterator
from contextlib import contextmanager

from fastapi.testclient import TestClient

from tests.fakes import (
    FakeReviewRepository,
    FakeUserActionRepository,
)
from ugc.application.content.services import (
    BookmarkApplicationService,
    LikeApplicationService,
    ReviewApplicationService,
)
from ugc.domain.content.user_id import UserId
from ugc.infrastructure.clock import SystemClock
from ugc.infrastructure.container import InfrastructureDependencyContainer
from ugc.infrastructure.mongo.client import MongoConnection
from ugc.infrastructure.security.token_verifier import JwtTokenVerifier
from ugc.infrastructure.settings import AppSettings
from ugc.presentation.api.application import build_application
from ugc.presentation.api.dependencies import (
    get_optional_user_id,
    get_required_user_id,
)
from ugc.presentation.container import ApplicationDependencyContainer


def _build_container() -> ApplicationDependencyContainer:
    settings = AppSettings.load()
    infrastructure = InfrastructureDependencyContainer(
        settings=settings,
        clock=SystemClock(),
        connection=MongoConnection(settings.mongo),
        like_repository=FakeUserActionRepository(),
        bookmark_repository=FakeUserActionRepository(),
        review_repository=FakeReviewRepository(),
        token_verifier=JwtTokenVerifier(settings.auth),
    )
    return ApplicationDependencyContainer(
        infrastructure=infrastructure,
        like_service=LikeApplicationService(
            infrastructure.like_repository, infrastructure.clock
        ),
        bookmark_service=BookmarkApplicationService(
            infrastructure.bookmark_repository, infrastructure.clock
        ),
        review_service=ReviewApplicationService(
            infrastructure.review_repository, infrastructure.clock
        ),
    )


@contextmanager
def _client(*, authorized: bool = True) -> Iterator[TestClient]:
    settings = AppSettings.load()
    container = _build_container()

    async def container_factory() -> ApplicationDependencyContainer:
        return container

    application = build_application(settings, container_factory)
    if authorized:
        application.dependency_overrides[get_required_user_id] = lambda: (
            UserId("user-1")
        )
        application.dependency_overrides[get_optional_user_id] = lambda: (
            UserId("user-1")
        )
    with TestClient(application) as client:
        yield client


def test_health_live() -> None:
    """Эндпоинт живости отвечает статусом ok."""
    with _client() as client:
        response = client.get("/health/live")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_add_like_and_read_status() -> None:
    """Лайк сохраняется и отражается в состоянии фильма."""
    with _client() as client:
        assert client.put("/api/v1/likes/film-1").status_code == 204
        response = client.get("/api/v1/likes/film-1")
    assert response.json() == {
        "film_id": "film-1",
        "count": 1,
        "liked_by_me": True,
    }


def test_remove_like() -> None:
    """Снятие лайка обнуляет состояние."""
    with _client() as client:
        client.put("/api/v1/likes/film-1")
        assert client.delete("/api/v1/likes/film-1").status_code == 204
        response = client.get("/api/v1/likes/film-1")
    assert response.json() == {
        "film_id": "film-1",
        "count": 0,
        "liked_by_me": False,
    }


def test_my_likes_list() -> None:
    """Список лайков пользователя возвращает фильмы."""
    with _client() as client:
        client.put("/api/v1/likes/film-1")
        client.put("/api/v1/likes/film-2")
        response = client.get("/api/v1/likes")
    assert sorted(response.json()["items"]) == ["film-1", "film-2"]


def test_bookmark_status() -> None:
    """Закладка сохраняется и отражается в состоянии."""
    with _client() as client:
        client.put("/api/v1/bookmarks/film-1")
        response = client.get("/api/v1/bookmarks/film-1")
    assert response.json() == {
        "film_id": "film-1",
        "count": 1,
        "bookmarked_by_me": True,
    }


def test_create_and_get_review() -> None:
    """Рецензия создаётся и читается по идентификатору."""
    with _client() as client:
        response = client.post(
            "/api/v1/reviews",
            json={"film_id": "film-1", "rating": 8, "text": "Отличный фильм"},
        )
        assert response.status_code == 201
        body = response.json()
        fetched = client.get(f"/api/v1/reviews/{body['review_id']}")
    assert body["rating"] == 8
    assert fetched.status_code == 200
    assert fetched.json()["text"] == "Отличный фильм"


def test_list_reviews_by_film() -> None:
    """Список рецензий фильма содержит все записи."""
    with _client() as client:
        client.post(
            "/api/v1/reviews",
            json={"film_id": "film-1", "rating": 8, "text": "a"},
        )
        client.post(
            "/api/v1/reviews",
            json={"film_id": "film-1", "rating": 7, "text": "b"},
        )
        response = client.get("/api/v1/reviews", params={"film_id": "film-1"})
    body = response.json()
    assert body["total"] == 2
    assert len(body["items"]) == 2


def test_create_review_rejects_invalid_rating() -> None:
    """Оценка вне диапазона отклоняется валидацией."""
    with _client() as client:
        response = client.post(
            "/api/v1/reviews",
            json={"film_id": "film-1", "rating": 11, "text": "x"},
        )
    assert response.status_code == 422


def test_get_missing_review_returns_404() -> None:
    """Чтение отсутствующей рецензии возвращает 404."""
    with _client() as client:
        response = client.get("/api/v1/reviews/missing")
    assert response.status_code == 404


def test_mutations_require_authentication() -> None:
    """Изменение контента без токена отклоняется с 401."""
    with _client(authorized=False) as client:
        assert client.put("/api/v1/likes/film-1").status_code == 401
        assert client.delete("/api/v1/likes/film-1").status_code == 401
        assert client.put("/api/v1/bookmarks/film-1").status_code == 401
        assert client.delete("/api/v1/bookmarks/film-1").status_code == 401
        assert (
            client.post(
                "/api/v1/reviews",
                json={"film_id": "film-1", "rating": 8, "text": "text"},
            ).status_code
            == 401
        )
        assert (
            client.patch(
                "/api/v1/reviews/review-1", json={"rating": 8, "text": "x"}
            ).status_code
            == 401
        )
        assert client.delete("/api/v1/reviews/review-1").status_code == 401


def test_personal_lists_require_authentication() -> None:
    """Личные списки без токена отклоняются с 401."""
    with _client(authorized=False) as client:
        assert client.get("/api/v1/likes").status_code == 401
        assert client.get("/api/v1/bookmarks").status_code == 401
        assert client.get("/api/v1/reviews/my").status_code == 401


def test_status_endpoints_are_public() -> None:
    """Статус лайка доступен без токена, флаг пользователя выключен."""
    with _client(authorized=False) as client:
        response = client.get("/api/v1/likes/film-1")
    assert response.status_code == 200
    assert response.json() == {
        "film_id": "film-1",
        "count": 0,
        "liked_by_me": False,
    }
