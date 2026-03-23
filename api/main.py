"""API entry: python -m uvicorn api.main:app with repo root on PYTHONPATH."""
from __future__ import annotations

import sys
from pathlib import Path

_API_DIR = Path(__file__).resolve().parent
_SRC = _API_DIR / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

from interfaces.http.main import create_app

app = create_app()
