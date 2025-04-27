#!/bin/bash
set -e

# Function to wait for a service
wait_for_service() {
  local host="$1"
  local port="$2"
  local service="$3"
  
  echo "Waiting for $service..."
  while ! nc -z "$host" "$port"; do
    echo "Waiting for $service at $host:$port..."
    sleep 1
  done
  echo "$service is up and running!"
}

# Wait for database to be ready
wait_for_service db 5432 "PostgreSQL"

# Wait for Redis to be ready
wait_for_service redis 6379 "Redis"

# Apply database migrations
echo "Applying database migrations..."
alembic upgrade head

# Determine which service to start based on the CONTAINER_ROLE environment variable
if [ "${CONTAINER_ROLE}" = "api" ] || [ -z "${CONTAINER_ROLE}" ]; then
  echo "Starting FastAPI application..."
  if [ "$ENVIRONMENT" = "production" ]; then
    uvicorn app.main:app --host 0.0.0.0 --port 8000 --proxy-headers
  else
    uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
  fi
elif [ "${CONTAINER_ROLE}" = "worker" ]; then
  echo "Starting Celery worker..."
  celery -A app.workers.celery_app worker --loglevel="${LOG_LEVEL:-INFO}"
elif [ "${CONTAINER_ROLE}" = "beat" ]; then
  echo "Starting Celery beat..."
  celery -A app.workers.celery_app beat --loglevel="${LOG_LEVEL:-INFO}"
elif [ "${CONTAINER_ROLE}" = "flower" ]; then
  echo "Starting Celery flower..."
  celery -A app.workers.celery_app flower --port=5555
else
  echo "Unknown CONTAINER_ROLE: ${CONTAINER_ROLE}"
  exit 1
fi