"""Тесты прикладных сервисов пользовательского контента."""

from datetime import UTC, datetime

import pytest

from ugc.application.content.services import (
    BookmarkApplicationService,
    LikeApplicationService,
    ReviewApplicationService,
)
from ugc.application.errors import (
    ReviewAccessDeniedError,
    ReviewNotFoundError,
)
from ugc.domain.content.film_id import FilmId
from ugc.domain.content.review import Review
from ugc.domain.content.review_id import ReviewId
from ugc.domain.content.user_action import UserAction
from ugc.domain.content.user_id import UserId


class FakeClock:
    """Часы с фиксированным временем."""

    def __init__(self) -> None:
        self._now = datetime(2026, 1, 1, tzinfo=UTC)

    def now(self) -> datetime:
        """Возвращает фиксированное время."""
        return self._now


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


def _like_service() -> tuple[LikeApplicationService, FakeUserActionRepository]:
    repository = FakeUserActionRepository()
    return LikeApplicationService(repository, FakeClock()), repository


def _bookmark_service() -> tuple[
    BookmarkApplicationService, FakeUserActionRepository
]:
    repository = FakeUserActionRepository()
    return BookmarkApplicationService(repository, FakeClock()), repository


def _review_service() -> tuple[ReviewApplicationService, FakeReviewRepository]:
    repository = FakeReviewRepository()
    return ReviewApplicationService(repository, FakeClock()), repository


async def test_like_add_is_idempotent() -> None:
    """Повторный лайк не создаёт вторую запись."""
    service, repository = _like_service()
    await service.add("user-1", "film-1")
    await service.add("user-1", "film-1")
    assert len(repository.actions) == 1
    assert await service.is_present("user-1", "film-1")


async def test_like_remove() -> None:
    """Снятие лайка удаляет запись."""
    service, _ = _like_service()
    await service.add("user-1", "film-1")
    await service.remove("user-1", "film-1")
    assert not await service.is_present("user-1", "film-1")


async def test_like_count_and_list() -> None:
    """Подсчёт и список лайков отражают сохранённые данные."""
    service, _ = _like_service()
    await service.add("user-1", "film-1")
    await service.add("user-2", "film-1")
    await service.add("user-1", "film-2")
    assert await service.count("film-1") == 2
    assert set(await service.list_film_ids("user-1")) == {
        FilmId("film-1"),
        FilmId("film-2"),
    }


async def test_bookmark_add() -> None:
    """Закладка сохраняется и доступна для чтения."""
    service, repository = _bookmark_service()
    await service.add("user-1", "film-1")
    assert len(repository.actions) == 1
    assert await service.is_present("user-1", "film-1")


async def test_review_create_and_get() -> None:
    """Созданная рецензия сохраняется и читается по идентификатору."""
    service, _ = _review_service()
    created = await service.create("user-1", "film-1", 8, "Отличный фильм")
    fetched = await service.get(created.review_id.value)
    assert fetched.rating == created.rating


async def test_review_update_by_author() -> None:
    """Автор может изменить оценку и текст рецензии."""
    service, _ = _review_service()
    created = await service.create("user-1", "film-1", 5, "Средне")
    updated = await service.update(
        created.review_id.value, "user-1", 9, "Пересмотрел"
    )
    assert updated.rating.value == 9
    assert str(updated.text) == "Пересмотрел"


async def test_review_update_by_other_is_denied() -> None:
    """Изменение чужой рецензии запрещено."""
    service, _ = _review_service()
    created = await service.create("user-1", "film-1", 5, "Средне")
    with pytest.raises(ReviewAccessDeniedError):
        await service.update(created.review_id.value, "user-2", 9, "Подмена")


async def test_review_delete_by_other_is_denied() -> None:
    """Удаление чужой рецензии запрещено."""
    service, _ = _review_service()
    created = await service.create("user-1", "film-1", 5, "Средне")
    with pytest.raises(ReviewAccessDeniedError):
        await service.delete(created.review_id.value, "user-2")


async def test_review_delete_by_author() -> None:
    """Автор может удалить свою рецензию."""
    service, _ = _review_service()
    created = await service.create("user-1", "film-1", 5, "Средне")
    await service.delete(created.review_id.value, "user-1")
    with pytest.raises(ReviewNotFoundError):
        await service.get(created.review_id.value)


async def test_review_get_missing_raises() -> None:
    """Чтение отсутствующей рецензии возвращает ошибку."""
    service, _ = _review_service()
    with pytest.raises(ReviewNotFoundError):
        await service.get("missing")
