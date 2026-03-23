#!/usr/bin/env bash
# Quick CI-style lock-in: lint + blocking architecture tests (same targets as scripts/lint.sh + validate_architecture.sh).
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

bash "$SCRIPT_DIR/lint.sh"
bash "$SCRIPT_DIR/validate_architecture.sh" --tb=short
