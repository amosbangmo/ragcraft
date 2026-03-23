#!/usr/bin/env bash
# Architecture lock-in: lint + import-boundary tests. Run from repo root via CI or locally.
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"
export PYTHONPATH="${PYTHONPATH:-.}"
echo "==> ruff check (src, apps, tests/architecture)"
ruff check src apps tests/architecture
echo "==> pytest tests/architecture"
pytest tests/architecture -q --tb=short
