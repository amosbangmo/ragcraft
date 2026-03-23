#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
export PYTHONPATH="${ROOT}/api/src:${ROOT}/frontend/src"
# Blocking layout + import-boundary guardrails (see docs/testing_strategy.md).
python -m pytest api/tests/architecture -q "$@"
