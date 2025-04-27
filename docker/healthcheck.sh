#!/bin/bash
set -e

# Determine what service to check based on CONTAINER_ROLE
if [ "${CONTAINER_ROLE}" = "api" ] || [ -z "${CONTAINER_ROLE}" ]; then
    # Check the API service
    curl --fail --silent --output /dev/null http://localhost:8000/health || exit 1
elif [ "${CONTAINER_ROLE}" = "worker" ]; then
    # Check Celery worker
    celery -A app.workers.celery_app inspect ping -d celery@$HOSTNAME || exit 1
elif [ "${CONTAINER_ROLE}" = "beat" ]; then
    # Check Celery beat (just check if the process is running)
    pgrep -f "celery -A app.workers.celery_app beat" || exit 1
elif [ "${CONTAINER_ROLE}" = "flower" ]; then
    # Check Flower (just check if we can connect to the port)
    curl --fail --silent --output /dev/null http://localhost:5555 || exit 1
else
    echo "Unknown container role: ${CONTAINER_ROLE}"
    exit 1
fi

# If we made it here, the service is healthy
exit 0 