#!/usr/bin/env bash
# Streamlit UI: sets PYTHONPATH for frontend/src + api/src, runs from frontend/.
# Usage (repo root): ./scripts/run_streamlit.sh [extra streamlit args]
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "${ROOT}/frontend"
export PYTHONPATH="${ROOT}/api/src:${ROOT}/frontend/src"
echo "==> python -m streamlit run app.py (cwd=$(pwd), PYTHONPATH set)"
exec python -m streamlit run app.py "$@"
