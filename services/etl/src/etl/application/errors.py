"""Ошибки прикладного слоя ETL."""


class ApplicationError(Exception):
    """Базовая ошибка прикладного слоя."""


class InvalidEventMessageError(ApplicationError):
    """Сообщение очереди не удалось преобразовать в событие."""
