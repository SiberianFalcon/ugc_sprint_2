"""Тесты HTTP-эндпоинтов сервиса контента."""

from fastapi.testclient import TestClient

from ugc.application.content.services import (
    BookmarkApplicationService,
    LikeApplicationService,
    ReviewApplicationService,
)
from ugc.domain.content.film_id import FilmId
from ugc.domain.content.review import Review
from ugc.domain.content.review_id import ReviewId
from ugc.domain.content.user_action import UserAction
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


class FakeUserActionRepository:
    """Хранилище действий в памяти."""

    def __init__(self) -> None:
        self.actions: dict[tuple[str, str], UserAction] = {}

    async def add(self, action: UserAction) -> None:
        self.actions[(action.user_id.value, action.film_id.value)] = action

    async def remove(self, user_id: UserId, film_id: FilmId) -> None:
        self.actions.pop((user_id.value, film_id.value), None)

    async def exists(self, user_id: UserId, film_id: FilmId) -> bool:
        return (user_id.value, film_id.value) in self.actions

    async def count_by_film(self, film_id: FilmId) -> int:
        return sum(
            1 for action in self.actions.values() if action.film_id == film_id
        )

    async def list_film_ids_by_user(self, user_id: UserId) -> list[FilmId]:
        return [
            action.film_id
            for action in self.actions.values()
            if action.user_id == user_id
        ]


class FakeReviewRepository:
    """Хранилище рецензий в памяти."""

    def __init__(self) -> None:
        self.reviews: dict[str, Review] = {}

    async def save(self, review: Review) -> None:
        self.reviews[review.review_id.value] = review

    async def get(self, review_id: ReviewId) -> Review | None:
        return self.reviews.get(review_id.value)

    async def delete(self, review_id: ReviewId) -> None:
        self.reviews.pop(review_id.value, None)

    async def list_by_film(
        self, film_id: FilmId, offset: int, limit: int
    ) -> list[Review]:
        matching = [
            review
            for review in self.reviews.values()
            if review.film_id == film_id
        ]
        return matching[offset : offset + limit]

    async def count_by_film(self, film_id: FilmId) -> int:
        return sum(
            1 for review in self.reviews.values() if review.film_id == film_id
        )

    async def list_by_user(self, user_id: UserId) -> list[Review]:
        return [
            review
            for review in self.reviews.values()
            if review.user_id == user_id
        ]


def _build_client(*, authorized: bool = True) -> TestClient:
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
    container = ApplicationDependencyContainer(
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
    application = build_application(settings, container)
    if authorized:
        application.dependency_overrides[get_required_user_id] = lambda: (
            UserId("user-1")
        )
        application.dependency_overrides[get_optional_user_id] = lambda: (
            UserId("user-1")
        )
    return TestClient(application)


def test_health_live() -> None:
    """Эндпоинт живости отвечает статусом ok."""
    response = _build_client().get("/health/live")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_add_like_and_read_status() -> None:
    """Лайк сохраняется и отражается в состоянии фильма."""
    client = _build_client()
    assert client.put("/api/v1/likes/film-1").status_code == 204
    response = client.get("/api/v1/likes/film-1")
    assert response.json() == {
        "film_id": "film-1",
        "count": 1,
        "liked_by_me": True,
    }


def test_remove_like() -> None:
    """Снятие лайка обнуляет состояние."""
    client = _build_client()
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
    client = _build_client()
    client.put("/api/v1/likes/film-1")
    client.put("/api/v1/likes/film-2")
    response = client.get("/api/v1/likes")
    assert sorted(response.json()["items"]) == ["film-1", "film-2"]


def test_bookmark_status() -> None:
    """Закладка сохраняется и отражается в состоянии."""
    client = _build_client()
    client.put("/api/v1/bookmarks/film-1")
    response = client.get("/api/v1/bookmarks/film-1")
    assert response.json() == {
        "film_id": "film-1",
        "count": 1,
        "bookmarked_by_me": True,
    }


def test_create_and_get_review() -> None:
    """Рецензия создаётся и читается по идентификатору."""
    client = _build_client()
    response = client.post(
        "/api/v1/reviews",
        json={"film_id": "film-1", "rating": 8, "text": "Отличный фильм"},
    )
    assert response.status_code == 201
    body = response.json()
    assert body["rating"] == 8
    fetched = client.get(f"/api/v1/reviews/{body['review_id']}")
    assert fetched.status_code == 200
    assert fetched.json()["text"] == "Отличный фильм"


def test_list_reviews_by_film() -> None:
    """Список рецензий фильма содержит все записи."""
    client = _build_client()
    client.post(
        "/api/v1/reviews", json={"film_id": "film-1", "rating": 8, "text": "a"}
    )
    client.post(
        "/api/v1/reviews", json={"film_id": "film-1", "rating": 7, "text": "b"}
    )
    response = client.get("/api/v1/reviews", params={"film_id": "film-1"})
    body = response.json()
    assert body["total"] == 2
    assert len(body["items"]) == 2


def test_create_review_rejects_invalid_rating() -> None:
    """Оценка вне диапазона отклоняется валидацией."""
    client = _build_client()
    response = client.post(
        "/api/v1/reviews",
        json={"film_id": "film-1", "rating": 11, "text": "x"},
    )
    assert response.status_code == 422


def test_get_missing_review_returns_404() -> None:
    """Чтение отсутствующей рецензии возвращает 404."""
    client = _build_client()
    assert client.get("/api/v1/reviews/missing").status_code == 404


def test_mutations_require_authentication() -> None:
    """Изменение контента без токена отклоняется с 401."""
    client = _build_client(authorized=False)
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
    client = _build_client(authorized=False)
    assert client.get("/api/v1/likes").status_code == 401
    assert client.get("/api/v1/bookmarks").status_code == 401
    assert client.get("/api/v1/reviews/my").status_code == 401


def test_status_endpoints_are_public() -> None:
    """Статус лайка доступен без токена, флаг пользователя выключен."""
    client = _build_client(authorized=False)
    response = client.get("/api/v1/likes/film-1")
    assert response.status_code == 200
    assert response.json() == {
        "film_id": "film-1",
        "count": 0,
        "liked_by_me": False,
    }
