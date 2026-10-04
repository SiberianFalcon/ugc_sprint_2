"""Маршруты работы с лайками."""

from fastapi import APIRouter, status

from ugc.presentation.api.dependencies import (
    LikeServiceDependency,
    OptionalUserIdDependency,
    RequiredUserIdDependency,
)
from ugc.presentation.api.schemas import FilmIdListResponse, LikeStatusResponse


router = APIRouter(prefix="/api/v1/likes", tags=["likes"])


@router.put("/{film_id}", status_code=status.HTTP_204_NO_CONTENT)
async def add_like(
    film_id: str,
    user_id: RequiredUserIdDependency,
    service: LikeServiceDependency,
) -> None:
    """Ставит лайк фильму, повторный вызов идемпотентен."""
    await service.add(str(user_id), film_id)


@router.delete("/{film_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_like(
    film_id: str,
    user_id: RequiredUserIdDependency,
    service: LikeServiceDependency,
) -> None:
    """Снимает лайк с фильма."""
    await service.remove(str(user_id), film_id)


@router.get("/{film_id}", response_model=LikeStatusResponse)
async def like_status(
    film_id: str,
    user_id: OptionalUserIdDependency,
    service: LikeServiceDependency,
) -> LikeStatusResponse:
    """Возвращает число лайков фильма и состояние пользователя."""
    count = await service.count(film_id)
    liked_by_me = user_id is not None and await service.is_present(
        str(user_id), film_id
    )
    return LikeStatusResponse(
        film_id=film_id, count=count, liked_by_me=liked_by_me
    )


@router.get("", response_model=FilmIdListResponse)
async def my_likes(
    user_id: RequiredUserIdDependency,
    service: LikeServiceDependency,
) -> FilmIdListResponse:
    """Возвращает фильмы, отмеченные пользователем."""
    film_ids = await service.list_film_ids(str(user_id))
    return FilmIdListResponse(items=[film.value for film in film_ids])
