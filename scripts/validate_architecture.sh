#!/usr/bin/env bash
# Blocking architecture guardrails: layout, required skeleton, import boundaries.
# Usage (repo root): ./scripts/validate_architecture.sh [extra pytest args]
# Same as: PYTHONPATH=api/src:frontend/src:api/tests pytest api/tests/architecture -q
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
export PYTHONPATH="${ROOT}/api/src:${ROOT}/frontend/src:${ROOT}/api/tests"

echo "==> Architecture tests (api/tests/architecture)"
python -m pytest api/tests/architecture -q "$@"
