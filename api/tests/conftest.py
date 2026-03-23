"""
Pytest-only hooks. (``unittest discover`` per folder is unaffected.)

Smoke tests replace entire ``sys.modules`` entries; they must run last so other
test modules are not imported while stubs are installed.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

_REPO_ROOT = Path(__file__).resolve().parents[2]
for _p in (
    _REPO_ROOT / "api" / "src",
    _REPO_ROOT / "frontend" / "src",
):
    s = str(_p.resolve())
    if s not in sys.path:
        sys.path.insert(0, s)


def pytest_configure(config) -> None:
    import os

    os.environ.setdefault(
        "RAGCRAFT_JWT_SECRET",
        "pytest-jwt-secret-key-minimum-32-characters-long!!",
    )
    # Register markers here so path-based auto-marking in ``pytest_collection_modifyitems`` never
    # triggers PytestUnknownMarkWarning when root ``pyproject.toml`` is not the active config file.
    for line in (
        "architecture: layout/import guardrails (api/tests/architecture)",
        "api_http: FastAPI TestClient routes (api/tests/api)",
        "appli: application use cases (api/tests/appli)",
        "e2e: regression / quality gates (api/tests/e2e)",
        "infra: infrastructure tests (api/tests/infra)",
        "bootstrap: ASGI entry smoke (api/tests/bootstrap)",
        "domain: domain tests (api/tests/domain)",
        "composition: composition smoke (api/tests/composition)",
        "frontend: frontend tests (frontend/tests)",
        "integration: cross-boundary HTTP walk (e.g. test_http_pipeline_e2e)",
    ):
        config.addinivalue_line("markers", line)


def pytest_collection_modifyitems(config, items) -> None:
    api_tests_dir = Path(__file__).resolve().parent
    frontend_tests_dir = _REPO_ROOT / "frontend" / "tests"

    for item in items:
        p = item.path.resolve()
        if api_tests_dir in p.parents:
            rel = p.relative_to(api_tests_dir)
            top = rel.parts[0] if rel.parts else ""
            if top == "architecture":
                item.add_marker(pytest.mark.architecture)
            elif top == "api":
                item.add_marker(pytest.mark.api_http)
            elif top == "appli":
                item.add_marker(pytest.mark.appli)
            elif top == "e2e":
                item.add_marker(pytest.mark.e2e)
            elif top == "infra":
                item.add_marker(pytest.mark.infra)
            elif top == "bootstrap":
                item.add_marker(pytest.mark.bootstrap)
            elif top == "domain":
                item.add_marker(pytest.mark.domain)
            elif top == "composition":
                item.add_marker(pytest.mark.composition)
        elif str(p).startswith(str(frontend_tests_dir.resolve())):
            item.add_marker(pytest.mark.frontend)
        if "test_http_pipeline_e2e" in item.nodeid:
            item.add_marker(pytest.mark.integration)

    smoke = [i for i in items if "test_smoke_upload_ingest_ask" in i.nodeid]
    if smoke:
        rest = [i for i in items if i not in smoke]
        items[:] = rest + smoke
