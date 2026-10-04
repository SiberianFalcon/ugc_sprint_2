"""Маршруты работы с закладками."""

from fastapi import APIRouter, status

from ugc.presentation.api.dependencies import (
    BookmarkServiceDependency,
    OptionalUserIdDependency,
    RequiredUserIdDependency,
)
from ugc.presentation.api.schemas import (
    BookmarkStatusResponse,
    FilmIdListResponse,
)


router = APIRouter(prefix="/api/v1/bookmarks", tags=["bookmarks"])


@router.put("/{film_id}", status_code=status.HTTP_204_NO_CONTENT)
async def add_bookmark(
    film_id: str,
    user_id: RequiredUserIdDependency,
    service: BookmarkServiceDependency,
) -> None:
    """Добавляет фильм в закладки, повторный вызов идемпотентен."""
    await service.add(str(user_id), film_id)


@router.delete("/{film_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_bookmark(
    film_id: str,
    user_id: RequiredUserIdDependency,
    service: BookmarkServiceDependency,
) -> None:
    """Удаляет фильм из закладок."""
    await service.remove(str(user_id), film_id)


@router.get("/{film_id}", response_model=BookmarkStatusResponse)
async def bookmark_status(
    film_id: str,
    user_id: OptionalUserIdDependency,
    service: BookmarkServiceDependency,
) -> BookmarkStatusResponse:
    """Возвращает число закладок фильма и состояние пользователя."""
    count = await service.count(film_id)
    bookmarked_by_me = user_id is not None and await service.is_present(
        str(user_id), film_id
    )
    return BookmarkStatusResponse(
        film_id=film_id, count=count, bookmarked_by_me=bookmarked_by_me
    )


@router.get("", response_model=FilmIdListResponse)
async def my_bookmarks(
    user_id: RequiredUserIdDependency,
    service: BookmarkServiceDependency,
) -> FilmIdListResponse:
    """Возвращает фильмы из закладок пользователя."""
    film_ids = await service.list_film_ids(str(user_id))
    return FilmIdListResponse(items=[film.value for film in film_ids])
