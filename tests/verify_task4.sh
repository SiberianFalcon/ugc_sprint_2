#!/usr/bin/env bash
# Сквозная проверка задания 4: API -> Kafka.
# Запускать из корня репозитория: sudo bash tests/verify_task4.sh
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

echo "############ CLEAN PREVIOUS STATE ############"
docker compose down -v --remove-orphans || true

echo "############ BUILD & UP (kafka + api) ############"
docker compose up -d --build api
echo "compose up exit=$?"

echo "############ WAIT FOR KAFKA ############"
wait_health kafka

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

echo "############ HEALTH ENDPOINTS ############"
echo -n "live:  "; curl -s http://localhost:8000/health/live; echo
echo -n "ready: "; curl -s http://localhost:8000/health/ready; echo

echo "############ SEND EVENTS ############"
echo -n "page_view: "
curl -s -X POST http://localhost:8000/events -H 'Content-Type: application/json' \
  -d '{"event_type":"page_view","payload":{"page_url":"https://example.com/movie","duration":120}}'
echo
echo -n "click (client id): "
curl -s -X POST http://localhost:8000/events -H 'Content-Type: application/json' \
  -d '{"event_type":"click","event_id":"fixed-1","payload":{"page_url":"/movie","element_id":"play"}}'
echo
echo -n "bad type http code: "
curl -s -o /dev/null -w '%{http_code}' -X POST http://localhost:8000/events \
  -H 'Content-Type: application/json' -d '{"event_type":"nope"}'
echo

sleep 2

echo "############ CONSUME FROM KAFKA TOPIC 'events' ############"
timeout -k 5 30 docker compose exec -T kafka \
  /opt/kafka/bin/kafka-console-consumer.sh \
  --bootstrap-server kafka:9092 \
  --topic events --from-beginning --property print.key=true \
  --max-messages 2 --timeout-ms 20000
echo "consumer exit=$?"

echo "############ API LOGS (tail) ############"
docker compose logs --no-color --tail 20 api

echo "############ DONE ############"
echo "Остановить: sudo docker compose down"
