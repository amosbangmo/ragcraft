"""
Required repository skeleton (PROMPT 3).

Asserts that canonical directories and **architectural anchor files** exist. This complements
forbidden-drift tests: it locks the **target tree**, not every future feature module.

**Test package naming:** the repo uses ``application_tests``, ``infrastructure_tests``, and
``apps_api`` under ``api/tests/`` (avoid shadowing ``application`` / ``infrastructure`` / ``api``
when ``api/src`` is on ``PYTHONPATH``). Those directories are the required counterparts to
“application / infrastructure / API” test areas.
"""

from __future__ import annotations

from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[3]


def _dir(path: Path) -> None:
    assert path.is_dir(), f"Missing required directory: {path.relative_to(REPO_ROOT)}"


def _file(path: Path) -> None:
    assert path.is_file(), f"Missing required file: {path.relative_to(REPO_ROOT)}"


@pytest.fixture(scope="module")
def repo_root() -> Path:
    return REPO_ROOT


def test_repository_level_directories(repo_root: Path) -> None:
    for rel in ("api", "frontend", "docs", "scripts"):
        _dir(repo_root / rel)


def test_backend_layer_directories(repo_root: Path) -> None:
    base = repo_root / "api" / "src"
    _dir(base / "domain")
    _dir(base / "application")
    _dir(base / "infrastructure")
    _dir(base / "composition")
    http = base / "interfaces" / "http"
    _dir(http)
    _dir(http / "routers")
    _dir(http / "schemas")


def test_backend_test_package_directories(repo_root: Path) -> None:
    t = repo_root / "api" / "tests"
    _dir(t / "architecture")
    _dir(t / "application_tests")
    _dir(t / "infrastructure_tests")
    _dir(t / "apps_api")
    _dir(t / "e2e")


def test_frontend_directories(repo_root: Path) -> None:
    fe = repo_root / "frontend"
    src = fe / "src"
    _dir(src / "pages")
    _dir(src / "components")
    _dir(src / "state")
    _dir(src / "services")
    _dir(fe / "tests")


def test_backend_top_level_key_files(repo_root: Path) -> None:
    api = repo_root / "api"
    _file(api / "main.py")
    _file(api / "pyproject.toml")
    _file(api / "README.md")


def test_composition_key_files(repo_root: Path) -> None:
    c = repo_root / "api" / "src" / "composition"
    for name in (
        "application_container.py",
        "backend_composition.py",
        "chat_rag_wiring.py",
        "evaluation_wiring.py",
        "auth_wiring.py",
    ):
        _file(c / name)


def test_fastapi_http_key_files(repo_root: Path) -> None:
    http = repo_root / "api" / "src" / "interfaces" / "http"
    for name in (
        "dependencies.py",
        "error_handlers.py",
        "error_payload.py",
        "upload_adapter.py",
    ):
        _file(http / name)


def test_fastapi_router_key_files(repo_root: Path) -> None:
    r = repo_root / "api" / "src" / "interfaces" / "http" / "routers"
    for name in (
        "auth.py",
        "users.py",
        "chat.py",
        "projects.py",
        "evaluation.py",
        "system.py",
    ):
        _file(r / name)


def test_fastapi_schema_key_files(repo_root: Path) -> None:
    s = repo_root / "api" / "src" / "interfaces" / "http" / "schemas"
    for name in (
        "auth.py",
        "users.py",
        "chat.py",
        "projects.py",
        "evaluation.py",
        "common.py",
    ):
        _file(s / name)


def test_frontend_top_level_key_files(repo_root: Path) -> None:
    fe = repo_root / "frontend"
    _file(fe / "app.py")
    _file(fe / "pyproject.toml")
    _file(fe / "README.md")


def test_frontend_structure_key_files(repo_root: Path) -> None:
    p = repo_root / "frontend" / "src"
    _file(p / "pages" / "chat.py")
    _file(p / "pages" / "projects.py")
    _file(p / "pages" / "evaluation.py")
    _file(p / "pages" / "settings.py")
    _file(p / "state" / "session_state.py")
    _file(p / "services" / "api_client.py")


def test_docs_and_script_key_files(repo_root: Path) -> None:
    docs = repo_root / "docs"
    for name in (
        "README.md",
        "architecture.md",
        "api.md",
        "rag_orchestration.md",
        "dependency_rules.md",
        "testing_strategy.md",
        "migration_report_final.md",
    ):
        _file(docs / name)
    scripts = repo_root / "scripts"
    for name in ("validate_architecture.sh", "run_tests.sh", "lint.sh"):
        _file(scripts / name)
