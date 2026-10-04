"""Ошибки прикладного слоя сервиса контента."""


class ApplicationError(Exception):
    """Базовая ошибка прикладного слоя."""


class ReviewNotFoundError(ApplicationError):
    """Рецензия не найдена."""


class ReviewAccessDeniedError(ApplicationError):
    """Пользователь не является автором рецензии."""


class ReviewConflictError(ApplicationError):
    """Рецензия изменена или удалена другим запросом."""


class InvalidTokenError(ApplicationError):
    """Токен доступа недействителен."""
