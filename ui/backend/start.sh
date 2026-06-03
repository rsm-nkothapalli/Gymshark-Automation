#!/usr/bin/env bash
# Start the GymsharkNexus FastAPI backend.
# Run from the repo root: bash ui/backend/start.sh

set -e
cd "$(dirname "$0")/../.."

echo "Starting GymsharkNexus on http://localhost:8001"
echo "API docs at http://localhost:8001/docs"
echo ""

uv run uvicorn ui.api.main:app --host 0.0.0.0 --reload --port 8001
