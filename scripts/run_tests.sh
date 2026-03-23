#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
export PYTHONPATH="${ROOT}/api/src:${ROOT}/frontend/src"
python -m pytest "${ROOT}/api/tests" "${ROOT}/frontend/tests" -q "$@"
