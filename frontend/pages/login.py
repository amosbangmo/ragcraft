"""Multipage shim: real module is ``frontend/src/pages/login.py``."""
from __future__ import annotations

import importlib.util
from pathlib import Path

_target = Path(__file__).resolve().parent.parent / "src" / "pages" / "login.py"
_spec = importlib.util.spec_from_file_location("ragcraft_streamlit_login_page", _target)
if _spec is None or _spec.loader is None:
    raise RuntimeError(f"Cannot load Streamlit page {_target}")
_mod = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_mod)
