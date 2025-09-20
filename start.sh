#!/bin/bash

# Get port from environment variable, default to 8000
PORT=${PORT:-8000}

echo "Starting server on port $PORT"

# Check if we should start worker (set WORKER=true in Railway env vars)
if [ "$WORKER" = "true" ]; then
    echo "Starting Celery worker..."
    celery -A celery_app worker --loglevel=info --concurrency=1 --queues=ai_processing &
    WORKER_PID=$!
    echo "Celery worker started with PID: $WORKER_PID"
fi

# Start the FastAPI server
uvicorn server:app --host 0.0.0.0 --port $PORT
