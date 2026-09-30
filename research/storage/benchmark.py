"""Сравнительное нагрузочное тестирование MongoDB и PostgreSQL.

Измеряет задержки типовых операций с пользовательским контентом:
точечное чтение, подсчёт, постраничный список, upsert и удаление.
Возвращает перцентили p50/p95/p99 в миллисекундах.
"""

from __future__ import annotations

import argparse
import json
import random
import time
from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path


_TYPE_BUCKETS: tuple[str, ...] = (
    "like",
    "like",
    "like",
    "like",
    "like",
    "like",
    "bookmark",
    "bookmark",
    "bookmark",
    "review",
)
_TYPE_BUCKET_COUNT = len(_TYPE_BUCKETS)
_WORKLOADS = (
    "read_point",
    "read_count",
    "read_list",
    "write_upsert",
    "delete",
)


def parse_args() -> argparse.Namespace:
    """Разбирает аргументы командной строки."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--records", type=int, default=10_000_000)
    parser.add_argument("--films", type=int, default=50_000)
    parser.add_argument("--ops", type=int, default=1_000)
    parser.add_argument("--warmup", type=int, default=200)
    parser.add_argument("--mongo-uri", default="mongodb://localhost:27018")
    parser.add_argument(
        "--postgres-dsn",
        default="postgresql://research:research@localhost:5433/research",
    )
    parser.add_argument(
        "--target", choices=("mongo", "postgres", "both"), default="both"
    )
    parser.add_argument(
        "--output",
        default="research/storage/results/latest.json",
    )
    return parser.parse_args()


def kind_for(index: int) -> str:
    """Возвращает тип записи по индексу с распределением 60/30/10."""
    return _TYPE_BUCKETS[index % _TYPE_BUCKET_COUNT]


def percentile(values: list[float], fraction: float) -> float:
    """Возвращает перцентиль отсортированного списка значений."""
    ordered = sorted(values)
    position = round(fraction * (len(ordered) - 1))
    return ordered[position]


def measure(
    operation: Callable[[], None], warmup: int, ops: int
) -> dict[str, float]:
    """Измеряет задержки операции и возвращает статистику в мс."""
    for _ in range(warmup):
        operation()
    latencies = []
    for _ in range(ops):
        started = time.perf_counter()
        operation()
        latencies.append((time.perf_counter() - started) * 1_000)
    return {
        "p50": round(percentile(latencies, 0.5), 3),
        "p95": round(percentile(latencies, 0.95), 3),
        "p99": round(percentile(latencies, 0.99), 3),
        "mean": round(sum(latencies) / len(latencies), 3),
    }


def run_mongo(
    uri: str, records: int, films: int, warmup: int, ops: int
) -> dict[str, dict[str, float]]:
    """Выполняет замеры для MongoDB."""
    from pymongo import MongoClient

    client = MongoClient(uri)
    collection = client["research"]["content"]
    rng = random.Random(1234)

    def point() -> None:
        index = rng.randrange(records)
        collection.find_one(
            {
                "user_id": f"user-{index}",
                "film_id": f"film-{index % films}",
                "kind": kind_for(index),
            }
        )

    def count() -> None:
        collection.count_documents(
            {"film_id": f"film-{rng.randrange(films)}", "kind": "like"}
        )

    def list_batch() -> None:
        cursor = (
            collection.find(
                {"film_id": f"film-{rng.randrange(films)}", "kind": "review"}
            )
            .sort("created_at", -1)
            .limit(20)
        )
        list(cursor)

    def upsert() -> None:
        index = rng.randrange(records)
        collection.update_one(
            {
                "user_id": f"user-{index}",
                "film_id": f"film-{index % films}",
                "kind": kind_for(index),
            },
            {"$set": {"created_at": datetime.now(UTC)}},
            upsert=True,
        )

    def remove() -> None:
        index = rng.randrange(records)
        collection.delete_one(
            {
                "user_id": f"user-{index}",
                "film_id": f"film-{index % films}",
                "kind": kind_for(index),
            }
        )

    operations = {
        "read_point": point,
        "read_count": count,
        "read_list": list_batch,
        "write_upsert": upsert,
        "delete": remove,
    }
    results = {
        name: measure(operations[name], warmup, ops) for name in _WORKLOADS
    }
    client.close()
    return results


def run_postgres(
    dsn: str, records: int, films: int, warmup: int, ops: int
) -> dict[str, dict[str, float]]:
    """Выполняет замеры для PostgreSQL."""
    import psycopg

    results: dict[str, dict[str, float]] = {}
    rng = random.Random(1234)
    with psycopg.connect(dsn, autocommit=True) as connection:  # noqa: SIM117
        with connection.cursor() as cursor:

            def point() -> None:
                index = rng.randrange(records)
                cursor.execute(
                    "SELECT user_id FROM content WHERE user_id=%s "
                    "AND film_id=%s AND kind=%s LIMIT 1",
                    (
                        f"user-{index}",
                        f"film-{index % films}",
                        kind_for(index),
                    ),
                )
                cursor.fetchall()

            def count() -> None:
                cursor.execute(
                    "SELECT count(*) FROM content "
                    "WHERE film_id=%s AND kind=%s",
                    (f"film-{rng.randrange(films)}", "like"),
                )
                cursor.fetchall()

            def list_batch() -> None:
                cursor.execute(
                    "SELECT user_id, rating, created_at FROM content "
                    "WHERE film_id=%s AND kind=%s "
                    "ORDER BY created_at DESC LIMIT 20",
                    (f"film-{rng.randrange(films)}", "review"),
                )
                cursor.fetchall()

            def upsert() -> None:
                index = rng.randrange(records)
                cursor.execute(
                    "INSERT INTO content "
                    "(user_id, film_id, kind, rating, review_text, "
                    "created_at) VALUES (%s, %s, %s, %s, %s, %s) "
                    "ON CONFLICT (user_id, film_id, kind) DO UPDATE "
                    "SET created_at=EXCLUDED.created_at",
                    (
                        f"user-{index}",
                        f"film-{index % films}",
                        kind_for(index),
                        0,
                        "",
                        datetime.now(UTC),
                    ),
                )

            def remove() -> None:
                index = rng.randrange(records)
                cursor.execute(
                    "DELETE FROM content WHERE user_id=%s "
                    "AND film_id=%s AND kind=%s",
                    (
                        f"user-{index}",
                        f"film-{index % films}",
                        kind_for(index),
                    ),
                )

            operations = {
                "read_point": point,
                "read_count": count,
                "read_list": list_batch,
                "write_upsert": upsert,
                "delete": remove,
            }
            for name in _WORKLOADS:
                results[name] = measure(operations[name], warmup, ops)
    return results


def render_table(
    results: dict[str, dict[str, dict[str, float]]],
) -> str:
    """Формирует markdown-таблицу с результатами."""
    header = (
        "| Операция | Хранилище | p50, мс | p95, мс | p99, мс | mean, мс |"
    )
    separator = "| --- | --- | --- | --- | --- | --- |"
    rows = [header, separator]
    for workload in _WORKLOADS:
        for storage, storage_results in results.items():
            metrics = storage_results[workload]
            rows.append(
                f"| {workload} | {storage} | {metrics['p50']} | "
                f"{metrics['p95']} | {metrics['p99']} | {metrics['mean']} |"
            )
    return "\n".join(rows)


def main() -> None:
    """Запускает замеры и сохраняет результаты."""
    args = parse_args()
    results: dict[str, dict[str, dict[str, float]]] = {}
    if args.target in ("mongo", "both"):
        results["mongo"] = run_mongo(
            args.mongo_uri, args.records, args.films, args.warmup, args.ops
        )
    if args.target in ("postgres", "both"):
        results["postgres"] = run_postgres(
            args.postgres_dsn,
            args.records,
            args.films,
            args.warmup,
            args.ops,
        )
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(results, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(render_table(results))
    print(f"\nРезультаты сохранены в {output}")


if __name__ == "__main__":
    main()
