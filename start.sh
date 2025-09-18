#!/bin/bash

# Get port from environment variable, default to 8000
PORT=${PORT:-8000}

echo "Starting server on port $PORT"

# Start the FastAPI server
uvicorn server:app --host 0.0.0.0 --port $PORT
