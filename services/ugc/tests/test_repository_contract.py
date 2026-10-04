"""Контрактные тесты репозиториев: тестовый двойник и MongoDB.

Набор проверок общий для обеих реализаций. MongoDB-вариант помечен
`integration` и требует переменную окружения `UGC_TEST_MONGO_URI`.
"""

import os
from collections.abc import AsyncIterator
from datetime import UTC, datetime, timedelta

import pytest
from motor.motor_asyncio import AsyncIOMotorClient

from tests.fakes import FakeReviewRepository, FakeUserActionRepository
from ugc.domain.content.created_at import CreatedAt
from ugc.domain.content.film_id import FilmId
from ugc.domain.content.like import Like
from ugc.domain.content.rating import Rating
from ugc.domain.content.review import Review
from ugc.domain.content.review_id import ReviewId
from ugc.domain.content.review_text import ReviewText
from ugc.domain.content.user_id import UserId
from ugc.infrastructure.mongo.review_repository import MongoReviewRepository
from ugc.infrastructure.mongo.user_action_repository import (
    MongoUserActionRepository,
)


MONGO_URI = os.getenv("UGC_TEST_MONGO_URI")
_TEST_DATABASE = "ugc_contract_test"
_BASE_TIME = datetime(2026, 1, 1, tzinfo=UTC)


@pytest.fixture(
    params=[
        pytest.param("fake"),
        pytest.param("mongo", marks=pytest.mark.integration),
    ]
)
def backend(request: pytest.FixtureRequest) -> str:
    """Параметр хранилища: тестовый двойник или MongoDB."""
    return str(request.param)


def _at(seconds: int) -> CreatedAt:
    return CreatedAt(_BASE_TIME + timedelta(seconds=seconds))


def _review(
    review_id: str,
    user_id: str,
    film_id: str,
    created: int,
    rating: int = 8,
    text: str = "Текст",
) -> Review:
    return Review(
        review_id=ReviewId(review_id),
        user_id=UserId(user_id),
        film_id=FilmId(film_id),
        rating=Rating(rating),
        text=ReviewText(text),
        created_at=_at(created),
        updated_at=_at(created),
    )


def _like(user_id: str, film_id: str, created: int) -> Like:
    return Like(UserId(user_id), FilmId(film_id), _at(created))


@pytest.fixture
async def review_repository(
    backend: str,
) -> AsyncIterator[FakeReviewRepository | MongoReviewRepository]:
    """Отдаёт реализацию ReviewRepository для текущего backend."""
    if backend == "fake":
        yield FakeReviewRepository()
        return
    uri = MONGO_URI
    if not uri:
        pytest.skip("UGC_TEST_MONGO_URI не задан")
    client: AsyncIOMotorClient = AsyncIOMotorClient(uri, tz_aware=True)
    collection = client[_TEST_DATABASE]["contract_reviews"]
    await collection.delete_many({})
    try:
        yield MongoReviewRepository(collection)
    finally:
        await collection.delete_many({})
        client.close()


@pytest.fixture
async def action_repository(
    backend: str,
) -> AsyncIterator[FakeUserActionRepository | MongoUserActionRepository]:
    """Отдаёт реализацию UserActionRepository для текущего backend."""
    if backend == "fake":
        yield FakeUserActionRepository()
        return
    uri = MONGO_URI
    if not uri:
        pytest.skip("UGC_TEST_MONGO_URI не задан")
    client: AsyncIOMotorClient = AsyncIOMotorClient(uri, tz_aware=True)
    collection = client[_TEST_DATABASE]["contract_actions"]
    await collection.delete_many({})
    try:
        yield MongoUserActionRepository(collection)
    finally:
        await collection.delete_many({})
        client.close()


async def test_review_create_and_get(
    review_repository: FakeReviewRepository | MongoReviewRepository,
) -> None:
    """Созданная рецензия читается со всеми полями."""
    await review_repository.create(_review("r1", "user-1", "film-1", 0))

    loaded = await review_repository.get(ReviewId("r1"))

    assert loaded is not None
    assert loaded.user_id == UserId("user-1")
    assert loaded.film_id == FilmId("film-1")
    assert loaded.rating == Rating(8)
    assert loaded.text == ReviewText("Текст")
    assert loaded.version == 0


async def test_review_get_missing_returns_none(
    review_repository: FakeReviewRepository | MongoReviewRepository,
) -> None:
    """Отсутствующая рецензия возвращает None."""
    assert await review_repository.get(ReviewId("missing")) is None


async def test_review_get_returns_independent_copy(
    review_repository: FakeReviewRepository | MongoReviewRepository,
) -> None:
    """Изменение прочитанного объекта не меняет хранилище без update."""
    await review_repository.create(_review("r1", "user-1", "film-1", 0))

    loaded = await review_repository.get(ReviewId("r1"))
    assert loaded is not None
    loaded.edit(Rating(1), ReviewText("changed"), _at(10))

    again = await review_repository.get(ReviewId("r1"))
    assert again is not None
    assert again.rating == Rating(8)
    assert again.version == 0


async def test_review_update_bumps_version(
    review_repository: FakeReviewRepository | MongoReviewRepository,
) -> None:
    """Успешное обновление сохраняет данные и увеличивает версию."""
    review = _review("r1", "user-1", "film-1", 0)
    await review_repository.create(review)
    review.edit(Rating(9), ReviewText("new"), _at(5))

    assert await review_repository.update(review, 0) is True

    loaded = await review_repository.get(ReviewId("r1"))
    assert loaded is not None
    assert loaded.rating == Rating(9)
    assert loaded.version == 1


async def test_review_update_rejects_stale_version(
    review_repository: FakeReviewRepository | MongoReviewRepository,
) -> None:
    """Устаревшая версия не даёт обновить рецензию."""
    review = _review("r1", "user-1", "film-1", 0)
    await review_repository.create(review)
    review.edit(Rating(9), ReviewText("new"), _at(5))

    assert await review_repository.update(review, 5) is False


async def test_review_update_does_not_resurrect_deleted(
    review_repository: FakeReviewRepository | MongoReviewRepository,
) -> None:
    """Обновление не возвращает удалённую рецензию."""
    review = _review("r1", "user-1", "film-1", 0)
    await review_repository.create(review)
    await review_repository.delete(ReviewId("r1"))
    review.edit(Rating(9), ReviewText("new"), _at(5))

    assert await review_repository.update(review, 0) is False
    assert await review_repository.get(ReviewId("r1")) is None


async def test_review_list_ordering_and_pagination(
    review_repository: FakeReviewRepository | MongoReviewRepository,
) -> None:
    """Список рецензий фильма идёт от новых к старым и лимитируется."""
    for index in range(5):
        await review_repository.create(
            _review(f"r{index}", "user-1", "film-1", index)
        )

    first = await review_repository.list_by_film(FilmId("film-1"), 0, 2)
    second = await review_repository.list_by_film(FilmId("film-1"), 2, 2)

    assert [review.review_id.value for review in first] == ["r4", "r3"]
    assert [review.review_id.value for review in second] == ["r2", "r1"]
    assert await review_repository.count_by_film(FilmId("film-1")) == 5


async def test_review_list_tiebreak_by_identifier(
    review_repository: FakeReviewRepository | MongoReviewRepository,
) -> None:
    """При равном времени порядок определяется идентификатором."""
    await review_repository.create(_review("a", "user-1", "film-1", 0))
    await review_repository.create(_review("b", "user-1", "film-1", 0))

    reviews = await review_repository.list_by_film(FilmId("film-1"), 0, 10)

    assert [review.review_id.value for review in reviews] == ["b", "a"]


async def test_review_list_by_user_and_count(
    review_repository: FakeReviewRepository | MongoReviewRepository,
) -> None:
    """Личный список рецензий фильтруется и считается по пользователю."""
    await review_repository.create(_review("r1", "user-1", "film-1", 0))
    await review_repository.create(_review("r2", "user-1", "film-2", 1))
    await review_repository.create(_review("r3", "user-2", "film-1", 2))

    reviews = await review_repository.list_by_user(UserId("user-1"), 0, 10)

    assert [review.review_id.value for review in reviews] == ["r2", "r1"]
    assert await review_repository.count_by_user(UserId("user-1")) == 2


async def test_action_add_is_idempotent(
    action_repository: FakeUserActionRepository | MongoUserActionRepository,
) -> None:
    """Повторное добавление действия не создаёт дубль."""
    await action_repository.add(_like("user-1", "film-1", 0))
    await action_repository.add(_like("user-1", "film-1", 0))

    assert await action_repository.exists(UserId("user-1"), FilmId("film-1"))
    assert await action_repository.count_by_film(FilmId("film-1")) == 1


async def test_action_remove(
    action_repository: FakeUserActionRepository | MongoUserActionRepository,
) -> None:
    """Удаление убирает действие из хранилища."""
    await action_repository.add(_like("user-1", "film-1", 0))

    await action_repository.remove(UserId("user-1"), FilmId("film-1"))

    assert not await action_repository.exists(
        UserId("user-1"), FilmId("film-1")
    )


async def test_action_lists_and_counts(
    action_repository: FakeUserActionRepository | MongoUserActionRepository,
) -> None:
    """Список действий пользователя упорядочен и лимитируется."""
    await action_repository.add(_like("user-1", "film-1", 0))
    await action_repository.add(_like("user-1", "film-2", 1))
    await action_repository.add(_like("user-2", "film-1", 2))

    film_ids = await action_repository.list_film_ids_by_user(
        UserId("user-1"), 0, 1
    )

    assert film_ids == [FilmId("film-2")]
    assert await action_repository.count_by_user(UserId("user-1")) == 2
    assert await action_repository.count_by_film(FilmId("film-1")) == 2
