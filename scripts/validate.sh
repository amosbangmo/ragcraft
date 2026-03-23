#!/usr/bin/env bash
# Architecture lock-in: lint + import-boundary tests. Run from repo root via CI or locally.
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"
export PYTHONPATH="${ROOT}/api/src:${ROOT}/frontend/src:${ROOT}/api/tests"
echo "==> ruff check (api/src, frontend/src, api/tests/architecture)"
ruff check api/src frontend/src api/tests/architecture
echo "==> pytest api/tests/architecture"
pytest api/tests/architecture -q --tb=short
