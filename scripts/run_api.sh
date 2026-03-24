#!/usr/bin/env bash
# FastAPI via uvicorn: PYTHONPATH is the repository root (so api.main resolves).
# Usage (repo root): ./scripts/run_api.sh [extra uvicorn args]
# Requires RAGCRAFT_JWT_SECRET (and other env) per docs — set in shell or .env loaded by your tooling.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
export PYTHONPATH="$ROOT"
echo "==> uvicorn api.main:app --reload --host 127.0.0.1 --port 8000 (cwd=$ROOT, PYTHONPATH=repo root)"
exec python -m uvicorn api.main:app --reload --host 127.0.0.1 --port 8000 "$@"
