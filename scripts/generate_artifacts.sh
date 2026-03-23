#!/usr/bin/env bash
# Generate artifacts/ (coverage, junit, benchmark text, CI-equivalent log).
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
exec python scripts/generate_artifacts.py "$@"
