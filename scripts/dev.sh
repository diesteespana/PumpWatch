#!/usr/bin/env bash
# Quick-start for local development.
set -euo pipefail

echo "🚀 Starting PumpWatch dev stack..."

cp -n .env.example .env 2>/dev/null && echo "✅ Created .env from example" || echo "ℹ️  .env already exists"

docker compose -f docker-compose.yml -f docker-compose.dev.yml up --build "$@"
