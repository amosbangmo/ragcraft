"""
Pytest-only hooks. (``unittest discover`` per folder is unaffected.)

Smoke tests replace entire ``sys.modules`` entries; they must run last so other
test modules are not imported while stubs are installed.
"""

from __future__ import annotations

import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[1]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))


def pytest_configure(config) -> None:
    import os

    os.environ.setdefault(
        "RAGCRAFT_JWT_SECRET",
        "pytest-jwt-secret-key-minimum-32-characters-long!!",
    )


def pytest_collection_modifyitems(config, items):
    smoke = [i for i in items if "test_smoke_upload_ingest_ask" in i.nodeid]
    if not smoke:
        return
    rest = [i for i in items if i not in smoke]
    items[:] = rest + smoke
