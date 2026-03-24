#!/usr/bin/env bash
# Ruff on application code and architecture tests (guardrail code is first-class).
# Typing: optional incremental mypy — see docs/testing_strategy.md
# Usage (repo root): ./scripts/lint.sh [extra ruff args]
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

echo "==> Ruff check (api/src, frontend/src, frontend/pages, api/tests/architecture)"
python -m ruff check "${ROOT}/api/src" "${ROOT}/frontend/src" "${ROOT}/frontend/pages" "${ROOT}/api/tests/architecture" "$@"
