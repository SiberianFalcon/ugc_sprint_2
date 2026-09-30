"""Тесты мониторинга потребления памяти."""

import asyncio
import logging

import pytest

from etl.infrastructure.monitoring.memory import MemoryMonitor


def test_reports_info_below_threshold(
    caplog: pytest.LogCaptureFixture,
) -> None:
    """При потреблении ниже порога пишется информационное сообщение."""
    monitor = MemoryMonitor(
        threshold_mb=100,
        interval_seconds=1.0,
        reader=lambda: 50.0,
    )

    with caplog.at_level(logging.INFO):
        monitor._report()

    assert any(record.levelno == logging.INFO for record in caplog.records)
    assert monitor.peak_mb == 50.0


def test_warns_above_threshold(
    caplog: pytest.LogCaptureFixture,
) -> None:
    """При превышении порога пишется предупреждение."""
    monitor = MemoryMonitor(
        threshold_mb=100,
        interval_seconds=1.0,
        reader=lambda: 150.0,
    )

    with caplog.at_level(logging.WARNING):
        monitor._report()

    assert any(record.levelno == logging.WARNING for record in caplog.records)


def test_peak_tracks_maximum() -> None:
    """Пик равен максимальному зафиксированному значению."""
    values = iter([10.0, 200.0, 30.0])
    monitor = MemoryMonitor(
        threshold_mb=1000,
        interval_seconds=1.0,
        reader=lambda: next(values),
    )

    monitor._report()
    monitor._report()
    monitor._report()

    assert monitor.peak_mb == 200.0


async def test_run_reports_periodically_and_stops() -> None:
    """Цикл измеряет память и завершается по stop()."""
    calls = 0

    def reader() -> float:
        nonlocal calls
        calls += 1
        return 10.0

    monitor = MemoryMonitor(
        threshold_mb=100,
        interval_seconds=0.01,
        reader=reader,
    )

    task = asyncio.create_task(monitor.run())
    await asyncio.sleep(0.05)
    await monitor.stop()
    await asyncio.wait_for(task, timeout=1)

    assert calls >= 1
