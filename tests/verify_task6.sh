#!/usr/bin/env bash
# Сквозная проверка задания 6: API -> Kafka -> ETL -> ClickHouse (+ дедупликация).
# Запускать из корня репозитория: sudo bash tests/verify_task6.sh
set -uo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
cd "$PROJECT_DIR"

wait_health() {
  local svc="$1" tries="${2:-60}" cid st
  for i in $(seq 1 "$tries"); do
    cid=$(docker compose ps -q "$svc" 2>/dev/null)
    st=$(docker inspect -f '{{if .State.Health}}{{.State.Health.Status}}{{else}}none{{end}}' "$cid" 2>/dev/null)
    if [ "$st" = "healthy" ]; then
      echo "$svc healthy (~$((i*2))s)"
      return 0
    fi
    sleep 2
  done
  echo "WARN: $svc not healthy in time"
  return 1
}

ch() {
  docker compose exec -T clickhouse clickhouse-client --query "$1"
}

echo "############ CLEAN PREVIOUS STATE ############"
docker compose down -v --remove-orphans || true

echo "############ BUILD & UP ############"
docker compose up -d --build
echo "compose up exit=$?"

echo "############ WAIT FOR KAFKA / CLICKHOUSE ############"
wait_health kafka
wait_health clickhouse

echo "############ CONTAINERS ############"
docker compose ps

echo "############ WAIT FOR API ############"
for i in $(seq 1 30); do
  if curl -sf http://localhost:8000/health/live >/dev/null 2>&1; then
    echo "api live (~$((i*2))s)"
    break
  fi
  sleep 2
done

echo "############ SEND EVENTS ############"
echo -n "page_view: "
curl -s -X POST http://localhost:8000/events -H 'Content-Type: application/json' \
  -d '{"user_id":"user-1","event_type":"page_view","payload":{"page_url":"https://example.com/movie","duration":120}}'
echo
echo -n "click dup-1 (1/2): "
curl -s -X POST http://localhost:8000/events -H 'Content-Type: application/json' \
  -d '{"user_id":"user-2","event_type":"click","event_id":"dup-1","payload":{"page_url":"/movie","element_id":"play"}}'
echo
echo -n "click dup-1 (2/2): "
curl -s -X POST http://localhost:8000/events -H 'Content-Type: application/json' \
  -d '{"user_id":"user-2","event_type":"click","event_id":"dup-1","payload":{"page_url":"/movie","element_id":"play"}}'
echo
echo -n "custom: "
curl -s -X POST http://localhost:8000/events -H 'Content-Type: application/json' \
  -d '{"user_id":"user-3","event_type":"custom","payload":{"event_name":"purchase","product_id":"p-42"}}'
echo

echo "############ WAIT FOR ETL TRANSFER (FINAL count) ############"
final=0
for i in $(seq 1 30); do
  final=$(ch "SELECT count() FROM ugc.events FINAL" 2>/dev/null | tr -d '[:space:]')
  if [ "${final:-0}" -ge 3 ] 2>/dev/null; then
    echo "unique events in ClickHouse: $final (~$((i*2))s)"
    break
  fi
  sleep 2
done

echo "############ RAW COUNT (с дублями) ############"
ch "SELECT count() AS raw_rows FROM ugc.events"

echo "############ FINAL COUNT (после дедупликации) ############"
ch "SELECT count() AS deduped_rows FROM ugc.events FINAL"

echo "############ ROWS ############"
ch "SELECT event_id, user_id, event_type, page_url, element_id, duration, event_name FROM ugc.events FINAL ORDER BY event_id FORMAT PrettyCompact"

echo "############ ETL LOGS (память) ############"
docker compose logs --no-color --tail 40 etl

echo "############ DONE ############"
echo "Остановить: sudo docker compose down"
echo "Удалить с данными: sudo docker compose down -v"
