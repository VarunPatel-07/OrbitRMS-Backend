#!/bin/bash

source .venv/bin/activate


set -e

echo "🚀 Running Docker Container for Valkey..."

docker compose up --build -d



sleep 3

echo "⚙️ Starting FastAPI Server..."
uvicorn index:app --reload