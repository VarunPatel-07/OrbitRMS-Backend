#!/bin/bash

source .venv/bin/activate

set -e

echo "🚀 Running Migration Command ...."

cd ./migrations/development

if alembic revision --autogenerate -m "automated-migration"; then
  echo "✅ Migration script generated successfully."
  echo ""

  sleep 2

  echo "📈 Now upgrading migration..."

  sleep 3

  alembic upgrade head
else
  echo "❌ Failed to generate migration script."
  exit 1
fi
