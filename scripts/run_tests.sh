#!/usr/bin/env bash
# Full pytest workflow: architecture guardrails first, then the rest of the suite (no duplicate run).
# Usage (repo root): ./scripts/run_tests.sh [extra pytest args passed to step 2 only]
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
export PYTHONPATH="${ROOT}/api/src:${ROOT}/frontend/src:${ROOT}/api/tests"
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

echo "==> Step 1/2: Architecture guardrails (blocking)"
bash "$SCRIPT_DIR/validate_architecture.sh"

echo "==> Step 2/2: Pytest — api/tests (except architecture/) + frontend/tests"
python -m pytest \
  "${ROOT}/api/tests" \
  --ignore="${ROOT}/api/tests/architecture" \
  --ignore="${ROOT}/api/tests/bootstrap" \
  "${ROOT}/frontend/tests" \
  -q "$@"
