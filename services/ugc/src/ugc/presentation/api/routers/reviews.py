"""Маршруты работы с рецензиями."""

from fastapi import APIRouter, Query, status

from ugc.domain.content.review import Review
from ugc.presentation.api.dependencies import (
    PageParamsDependency,
    RequiredUserIdDependency,
    ReviewServiceDependency,
)
from ugc.presentation.api.schemas import (
    ReviewCreateRequest,
    ReviewListResponse,
    ReviewResponse,
    ReviewUpdateRequest,
)


router = APIRouter(prefix="/api/v1/reviews", tags=["reviews"])


@router.post("", status_code=status.HTTP_201_CREATED)
async def create_review(
    body: ReviewCreateRequest,
    user_id: RequiredUserIdDependency,
    service: ReviewServiceDependency,
) -> ReviewResponse:
    """Создаёт рецензию пользователя на фильм."""
    review = await service.create(
        str(user_id), body.film_id, body.rating, body.text
    )
    return _to_response(review)


@router.get("", response_model=ReviewListResponse)
async def list_reviews(
    service: ReviewServiceDependency,
    page_params: PageParamsDependency,
    film_id: str = Query(min_length=1),
) -> ReviewListResponse:
    """Возвращает страницу рецензий фильма."""
    reviews = await service.list_by_film(
        film_id, page_params.offset, page_params.page_size
    )
    total = await service.count_by_film(film_id)
    return ReviewListResponse(
        items=[_to_response(review) for review in reviews],
        total=total,
        page=page_params.page,
        page_size=page_params.page_size,
    )


@router.get("/my", response_model=ReviewListResponse)
async def my_reviews(
    user_id: RequiredUserIdDependency,
    page_params: PageParamsDependency,
    service: ReviewServiceDependency,
) -> ReviewListResponse:
    """Возвращает страницу рецензий текущего пользователя."""
    reviews = await service.list_by_user(
        str(user_id), page_params.offset, page_params.page_size
    )
    total = await service.count_by_user(str(user_id))
    return ReviewListResponse(
        items=[_to_response(review) for review in reviews],
        total=total,
        page=page_params.page,
        page_size=page_params.page_size,
    )


@router.get("/{review_id}", response_model=ReviewResponse)
async def get_review(
    review_id: str,
    service: ReviewServiceDependency,
) -> ReviewResponse:
    """Возвращает рецензию по идентификатору."""
    return _to_response(await service.get(review_id))


@router.patch("/{review_id}", response_model=ReviewResponse)
async def update_review(
    review_id: str,
    body: ReviewUpdateRequest,
    user_id: RequiredUserIdDependency,
    service: ReviewServiceDependency,
) -> ReviewResponse:
    """Изменяет рецензию, если пользователь является её автором."""
    review = await service.update(
        review_id, str(user_id), body.rating, body.text
    )
    return _to_response(review)


@router.delete("/{review_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_review(
    review_id: str,
    user_id: RequiredUserIdDependency,
    service: ReviewServiceDependency,
) -> None:
    """Удаляет рецензию, если пользователь является её автором."""
    await service.delete(review_id, str(user_id))


def _to_response(review: Review) -> ReviewResponse:
    return ReviewResponse(
        review_id=review.review_id.value,
        user_id=review.user_id.value,
        film_id=review.film_id.value,
        rating=review.rating.value,
        text=review.text.value,
        created_at=review.created_at.value.isoformat(),
        updated_at=review.updated_at.value.isoformat(),
    )
