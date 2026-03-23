#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
export PYTHONPATH="${ROOT}/api/src"
python -m pytest "${ROOT}/api/tests/architecture" -q "$@"
