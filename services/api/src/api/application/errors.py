"""Ошибки прикладного слоя API."""


class ApplicationError(Exception):
    """Базовая ошибка прикладного слоя."""


class InvalidTokenError(ApplicationError):
    """Токен недействителен или не содержит идентификатор пользователя."""
