"""Blocking checks that the repository matches the target physical layout (PROMPT 1)."""

from __future__ import annotations

from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[3]


def _must_dir(path: Path) -> None:
    assert path.is_dir(), f"Missing required directory: {path.relative_to(REPO_ROOT)}"


def _must_not_exist(path: Path) -> None:
    assert not path.exists(), f"Obsolete path must not exist: {path.relative_to(REPO_ROOT)}"


def test_no_legacy_root_src_or_apps() -> None:
    _must_not_exist(REPO_ROOT / "src")
    _must_not_exist(REPO_ROOT / "apps")


def test_api_backend_tree() -> None:
    api = REPO_ROOT / "api"
    src = api / "src"
    _must_dir(api)
    _must_dir(src)
    _must_dir(src / "domain" / "auth")
    _must_dir(src / "domain" / "users")
    _must_dir(src / "domain" / "projects")
    _must_dir(src / "domain" / "rag")
    _must_dir(src / "domain" / "evaluation")
    _must_dir(src / "domain" / "common")
    _must_dir(src / "application" / "dto")
    _must_dir(src / "application" / "ports")
    _must_dir(src / "application" / "use_cases")
    _must_dir(src / "application" / "orchestration" / "rag")
    _must_dir(src / "application" / "orchestration" / "evaluation")
    _must_dir(src / "application" / "policies")
    _must_dir(src / "application" / "services")
    _must_dir(src / "application" / "http" / "wire")
    _must_dir(src / "infrastructure" / "auth")
    _must_dir(src / "infrastructure" / "persistence")
    _must_dir(src / "infrastructure" / "storage")
    _must_dir(src / "infrastructure" / "rag")
    _must_dir(src / "infrastructure" / "evaluation")
    _must_dir(src / "infrastructure" / "observability")
    _must_dir(src / "infrastructure" / "config")
    _must_dir(src / "composition")
    _must_dir(src / "interfaces" / "http" / "routers")
    _must_dir(src / "interfaces" / "http" / "schemas")
    assert (api / "main.py").is_file()


def test_frontend_tree() -> None:
    fe = REPO_ROOT / "frontend"
    src = fe / "src"
    _must_dir(fe)
    _must_dir(src / "pages")
    _must_dir(src / "components" / "chat")
    _must_dir(src / "components" / "projects")
    _must_dir(src / "components" / "shared")
    _must_dir(src / "state")
    _must_dir(src / "services")
    _must_dir(src / "viewmodels")
    _must_dir(src / "utils")
    assert (fe / "app.py").is_file()


def test_docs_and_scripts() -> None:
    docs = REPO_ROOT / "docs"
    for name in (
        "README.md",
        "architecture.md",
        "api.md",
        "rag_orchestration.md",
        "dependency_rules.md",
        "testing_strategy.md",
        "migration_report_final.md",
    ):
        assert (docs / name).is_file(), f"Missing docs/{name}"
    scripts = REPO_ROOT / "scripts"
    for name in ("validate_architecture.sh", "run_tests.sh", "lint.sh"):
        assert (scripts / name).is_file(), f"Missing scripts/{name}"


def test_no_obsolete_infrastructure_adapters_package() -> None:
    _must_not_exist(REPO_ROOT / "api" / "src" / "infrastructure" / "adapters")
