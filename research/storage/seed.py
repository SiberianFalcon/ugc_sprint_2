"""Наполнение MongoDB и PostgreSQL синтетическими данными для исследования.

Данные имитируют пользовательский контент: лайки, закладки и рецензии.
Распределение типов — 60% лайки, 30% закладки, 10% рецензии.
Идентификатор пользователя уникален для записи, что гарантирует
уникальность пары (user_id, film_id, kind).
"""

from __future__ import annotations

import argparse
import random
import time
from collections.abc import Iterator
from datetime import UTC, datetime, timedelta


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
_WINDOW_SECONDS = 30 * 24 * 60 * 60

Record = tuple[str, str, str, int, str, datetime]


def parse_args() -> argparse.Namespace:
    """Разбирает аргументы командной строки."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--records", type=int, default=10_000_000)
    parser.add_argument("--films", type=int, default=50_000)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--batch-size", type=int, default=10_000)
    parser.add_argument("--mongo-uri", default="mongodb://localhost:27018")
    parser.add_argument(
        "--postgres-dsn",
        default="postgresql://research:research@localhost:5433/research",
    )
    parser.add_argument(
        "--target", choices=("mongo", "postgres", "both"), default="both"
    )
    return parser.parse_args()


def record_iter(records: int, films: int, seed: int) -> Iterator[Record]:
    """Порождает синтетические записи контента."""
    rng = random.Random(seed)
    start_time = datetime.now(UTC)
    for index in range(records):
        kind = _TYPE_BUCKETS[index % len(_TYPE_BUCKETS)]
        rating = rng.randint(1, 10) if kind == "review" else 0
        text = f"review-{index}" if kind == "review" else ""
        created_at = start_time - timedelta(seconds=index % _WINDOW_SECONDS)
        yield (
            f"user-{index}",
            f"film-{index % films}",
            kind,
            rating,
            text,
            created_at,
        )


def seed_mongo(
    uri: str, records: int, films: int, seed: int, batch_size: int
) -> None:
    """Загружает записи в MongoDB и строит индексы."""
    from pymongo import MongoClient

    client = MongoClient(uri)
    collection = client["research"]["content"]
    collection.drop()
    batch: list[dict[str, object]] = []
    for user_id, film_id, kind, rating, text, created_at in record_iter(
        records, films, seed
    ):
        batch.append(
            {
                "user_id": user_id,
                "film_id": film_id,
                "kind": kind,
                "rating": rating,
                "review_text": text,
                "created_at": created_at,
            }
        )
        if len(batch) >= batch_size:
            collection.insert_many(batch, ordered=False)
            batch.clear()
    if batch:
        collection.insert_many(batch, ordered=False)
    collection.create_index(
        [("user_id", 1), ("film_id", 1), ("kind", 1)],
        unique=True,
        name="uniq_user_film_kind",
    )
    collection.create_index(
        [("film_id", 1), ("kind", 1), ("created_at", -1)],
        name="film_kind_created",
    )
    client.close()


def seed_postgres(dsn: str, records: int, films: int, seed: int) -> None:
    """Загружает записи в PostgreSQL через COPY и строит индексы."""
    import psycopg

    with psycopg.connect(dsn, autocommit=True) as connection:  # noqa: SIM117
        with connection.cursor() as cursor:
            cursor.execute("DROP TABLE IF EXISTS content")
            cursor.execute(
                """
                CREATE TABLE content (
                    user_id text NOT NULL,
                    film_id text NOT NULL,
                    kind text NOT NULL,
                    rating integer NOT NULL DEFAULT 0,
                    review_text text NOT NULL DEFAULT '',
                    created_at timestamptz NOT NULL
                )
                """
            )
            copy_sql = (
                "COPY content "
                "(user_id, film_id, kind, rating, review_text, created_at) "
                "FROM STDIN"
            )
            with cursor.copy(copy_sql) as copy:
                for record in record_iter(records, films, seed):
                    copy.write_row(record)
            cursor.execute(
                "CREATE UNIQUE INDEX uniq_user_film_kind "
                "ON content (user_id, film_id, kind)"
            )
            cursor.execute(
                "CREATE INDEX film_kind_created "
                "ON content (film_id, kind, created_at DESC)"
            )


def main() -> None:
    """Запускает наполнение выбранных хранилищ."""
    args = parse_args()
    if args.target in ("mongo", "both"):
        started = time.perf_counter()
        seed_mongo(
            args.mongo_uri,
            args.records,
            args.films,
            args.seed,
            args.batch_size,
        )
        elapsed = time.perf_counter() - started
        print(f"MongoDB: загружено {args.records} записей за {elapsed:.1f}s")
    if args.target in ("postgres", "both"):
        started = time.perf_counter()
        seed_postgres(args.postgres_dsn, args.records, args.films, args.seed)
        elapsed = time.perf_counter() - started
        print(
            f"PostgreSQL: загружено {args.records} записей за {elapsed:.1f}s"
        )


if __name__ == "__main__":
    main()
