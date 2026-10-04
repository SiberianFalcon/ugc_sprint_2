"""Тесты прикладных сервисов пользовательского контента."""

import pytest

from tests.fakes import (
    FakeClock,
    FakeReviewRepository,
    FakeUserActionRepository,
)
from ugc.application.content.services import (
    BookmarkApplicationService,
    LikeApplicationService,
    ReviewApplicationService,
)
from ugc.application.errors import (
    ReviewAccessDeniedError,
    ReviewConflictError,
    ReviewNotFoundError,
)
from ugc.domain.content.film_id import FilmId


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
    assert len(repository.documents) == 1
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
    assert len(repository.documents) == 1
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


async def test_review_update_detects_version_conflict() -> None:
    """Конфликт версий при обновлении приводит к ошибке."""

    class _ConflictingRepository(FakeReviewRepository):
        async def update(self, review: object, expected_version: int) -> bool:
            return False

    repository = _ConflictingRepository()
    service = ReviewApplicationService(repository, FakeClock())
    created = await service.create("user-1", "film-1", 5, "Средне")
    with pytest.raises(ReviewConflictError):
        await service.update(created.review_id.value, "user-1", 9, "Новое")
