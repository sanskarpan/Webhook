#!/bin/bash
set -e

# Wait for database to be ready
echo "Waiting for PostgreSQL..."
while ! nc -z db 5432; do
  sleep 0.1
done
echo "PostgreSQL is up and running"

# Wait for Redis to be ready
echo "Waiting for Redis..."
while ! nc -z redis 6379; do
  sleep 0.1
done
echo "Redis is up and running"

# Apply database migrations
echo "Applying database migrations..."
alembic upgrade head

# Start the FastAPI application
echo "Starting FastAPI application..."
if [ "$ENVIRONMENT" = "production" ]; then
  uvicorn app.main:app --host 0.0.0.0 --port 8000 --proxy-headers
else
  uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
fi