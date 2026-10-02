#!/usr/bin/env bash
# Стенд исследования хранилищ MongoDB и PostgreSQL.
# Запускать из корня репозитория без sudo:
#   bash research/storage/run.sh
# При необходимости скрипт сам вызовет sudo для docker.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$(dirname "$SCRIPT_DIR")")"
cd "$PROJECT_DIR"

if docker info >/dev/null 2>&1; then
  DOCKER="docker"
else
  DOCKER="sudo docker"
fi
COMPOSE="$DOCKER compose -f research/storage/docker-compose.research.yml"
RECORDS="${RECORDS:-10000000}"

wait_healthy() {
  local svc="$1" tries="${2:-90}" cid st
  for i in $(seq 1 "$tries"); do
    cid=$($COMPOSE ps -q "$svc" 2>/dev/null)
    st=$($DOCKER inspect -f '{{if .State.Health}}{{.State.Health.Status}}{{else}}none{{end}}' "$cid" 2>/dev/null)
    if [ "$st" = "healthy" ]; then
      echo "$svc healthy (~$((i*2))s)"
      return 0
    fi
    sleep 2
  done
  echo "WARN: $svc not healthy in time"
  return 1
}

echo "############ UP ############"
$COMPOSE up -d
wait_healthy mongo
wait_healthy postgres

echo "############ SEED ($RECORDS records) ############"
uv run --with 'psycopg[binary]' python research/storage/seed.py \
  --records "$RECORDS"

echo "############ BENCHMARK ############"
uv run --with 'psycopg[binary]' python research/storage/benchmark.py \
  --records "$RECORDS"

echo "############ DONE ############"
echo "Остановить:          $COMPOSE down"
echo "Остановить с данными: $COMPOSE down -v"
