#!/usr/bin/env bash
set -euo pipefail

# Apply database migrations on each deploy/start.
alembic upgrade head

# Render injects PORT at runtime.
exec uvicorn app.main:app --host 0.0.0.0 --port "${PORT}"
