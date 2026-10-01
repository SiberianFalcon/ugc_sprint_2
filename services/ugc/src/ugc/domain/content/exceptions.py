"""Ошибки агрегатов пользовательского контента."""

from ugc.domain.exceptions import DomainError


class ContentError(DomainError):
    """Базовая ошибка пользовательского контента."""


class InvalidUserIdError(ContentError):
    """Идентификатор пользователя не соответствует требованиям."""


class InvalidFilmIdError(ContentError):
    """Идентификатор фильма не соответствует требованиям."""


class InvalidReviewIdError(ContentError):
    """Идентификатор рецензии не соответствует требованиям."""


class InvalidReviewTextError(ContentError):
    """Текст рецензии не соответствует требованиям."""


class InvalidRatingError(ContentError):
    """Оценка рецензии не соответствует требованиям."""


class InvalidCreatedAtError(ContentError):
    """Момент времени не соответствует требованиям."""
