"""Мониторинг потребления памяти процессом."""

import asyncio
import logging
from collections.abc import Callable
from contextlib import suppress

import psutil


logger = logging.getLogger(__name__)


def _read_process_rss_mb() -> float:
    rss_bytes = float(psutil.Process().memory_info().rss)
    return rss_bytes / (1024 * 1024)


class MemoryMonitor:
    """Периодически сообщает о потреблении памяти процессом."""

    def __init__(
        self,
        threshold_mb: int,
        interval_seconds: float,
        reader: Callable[[], float] | None = None,
    ) -> None:
        self._threshold_mb = threshold_mb
        self._interval_seconds = interval_seconds
        self._reader = reader or _read_process_rss_mb
        self._peak_mb = 0.0
        self._stopped = asyncio.Event()

    @property
    def peak_mb(self) -> float:
        """Возвращает пиковое потребление памяти в мегабайтах."""
        return self._peak_mb

    async def run(self) -> None:
        """Периодически измеряет и логирует потребление памяти."""
        while not self._stopped.is_set():
            self._report()
            await self._wait_interval()

    async def stop(self) -> None:
        """Останавливает мониторинг."""
        self._stopped.set()

    def _report(self) -> None:
        current_mb = self._reader()
        self._peak_mb = max(self._peak_mb, current_mb)
        if current_mb >= self._threshold_mb:
            logger.warning(
                "Память %s МБ превышает порог %s МБ (пик %s МБ).",
                round(current_mb, 1),
                self._threshold_mb,
                round(self._peak_mb, 1),
            )
            return
        logger.info(
            "Память %s МБ (пик %s МБ).",
            round(current_mb, 1),
            round(self._peak_mb, 1),
        )

    async def _wait_interval(self) -> None:
        with suppress(TimeoutError):
            await asyncio.wait_for(
                self._stopped.wait(), timeout=self._interval_seconds
            )
