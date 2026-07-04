#!/bin/bash

set -e

source .venv/bin/activate

echo "🚀 Running Docker Container for Valkey..."
docker compose up --build -d

sleep 3

echo "⚙️ Starting FastAPI Server..."
uvicorn index:app --reload &
UVICORN_PID=$!

echo "📨 Starting ARQ Worker..."
arq mailer.emailService.worker.WorkerSettings &
ARQ_PID=$!

cleanup() {
  echo "🛑 Stopping services..."
  kill "$UVICORN_PID" "$ARQ_PID" 2>/dev/null || true
}

trap cleanup INT TERM EXIT

echo "✅ FastAPI PID: $UVICORN_PID"
echo "✅ ARQ Worker PID: $ARQ_PID"

# Keep checking if both processes are alive
while true; do
  if ! kill -0 "$UVICORN_PID" 2>/dev/null; then
    echo "❌ FastAPI server stopped. Shutting down ARQ worker..."
    cleanup
    exit 1
  fi

  if ! kill -0 "$ARQ_PID" 2>/dev/null; then
    echo "❌ ARQ worker stopped. Shutting down FastAPI server..."
    cleanup
    exit 1
  fi

  sleep 2
done