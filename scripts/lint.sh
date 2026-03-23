#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
python -m ruff check "${ROOT}/api/src" "${ROOT}/frontend/src" "$@"
