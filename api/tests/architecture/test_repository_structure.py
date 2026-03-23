"""
Blocking physical layout checks (PROMPT 2).

Fails on structural drift: missing roots, legacy folders, misplaced HTTP routers/schemas,
or orchestration living outside ``application/orchestration/``.
"""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[3]
API_SRC = REPO_ROOT / "api" / "src"
HTTP = API_SRC / "interfaces" / "http"

# Only these files may live directly under interfaces/http/ (no extra modules).
_HTTP_ROOT_FILES = frozenset(
    {
        "__init__.py",
        "config.py",
        "dependencies.py",
        "error_handlers.py",
        "error_payload.py",
        "main.py",
        "openapi_common.py",
        "upload_adapter.py",
    }
)
_HTTP_SUBDIRS = frozenset({"routers", "schemas"})


def _must_dir(path: Path) -> None:
    assert path.is_dir(), f"Missing required directory: {path.relative_to(REPO_ROOT)}"


def _must_not_exist(path: Path) -> None:
    assert not path.exists(), f"Forbidden path exists: {path.relative_to(REPO_ROOT)}"


def test_required_top_level_roots_exist() -> None:
    for p in (
        REPO_ROOT / "api",
        REPO_ROOT / "frontend",
        REPO_ROOT / "api" / "src",
        REPO_ROOT / "frontend" / "src",
        REPO_ROOT / "docs",
        REPO_ROOT / "scripts",
    ):
        _must_dir(p)


def test_legacy_root_packages_absent() -> None:
    _must_not_exist(REPO_ROOT / "src")
    _must_not_exist(REPO_ROOT / "apps")
    _must_not_exist(REPO_ROOT / "pages")
    _must_not_exist(REPO_ROOT / "streamlit_app.py")


def test_backend_python_sources_live_only_under_api_src() -> None:
    """Backend application code must not accumulate under ``api/`` outside ``api/src/`` (plus entry + tests)."""
    api_dir = REPO_ROOT / "api"
    for path in api_dir.rglob("*.py"):
        if "__pycache__" in path.parts:
            continue
        rel = path.relative_to(api_dir)
        parts = rel.parts
        if parts in (("main.py",), ("__init__.py",)):
            continue
        if parts and parts[0] == "src":
            continue
        if parts and parts[0] == "tests":
            continue
        pytest.fail(
            f"Unexpected Python file under api/ (use api/src/ or api/tests/): "
            f"{path.relative_to(REPO_ROOT)}"
        )


def test_frontend_python_sources_live_only_under_frontend_src() -> None:
    """Frontend application code must not live under ``frontend/`` outside ``frontend/src/`` (plus entry + tests)."""
    fe = REPO_ROOT / "frontend"
    for path in fe.rglob("*.py"):
        if "__pycache__" in path.parts:
            continue
        rel = path.relative_to(fe)
        parts = rel.parts
        if parts == ("app.py",):
            continue
        if parts and parts[0] == "src":
            continue
        if parts and parts[0] == "tests":
            continue
        pytest.fail(
            f"Unexpected Python file under frontend/ (use frontend/src/ or frontend/tests/): "
            f"{path.relative_to(REPO_ROOT)}"
        )


def test_obsolete_infrastructure_adapters_package_absent() -> None:
    _must_not_exist(API_SRC / "infrastructure" / "adapters")


def test_api_entrypoint_exists() -> None:
    assert (REPO_ROOT / "api" / "main.py").is_file()


def test_core_backend_directories_exist() -> None:
    _must_dir(API_SRC / "domain" / "auth")
    _must_dir(API_SRC / "domain" / "projects")
    _must_dir(API_SRC / "domain" / "rag")
    _must_dir(API_SRC / "domain" / "evaluation")
    _must_dir(API_SRC / "domain" / "common")
    _must_dir(API_SRC / "application" / "dto")
    _must_dir(API_SRC / "application" / "ports")
    _must_dir(API_SRC / "application" / "use_cases")
    _must_dir(API_SRC / "application" / "orchestration" / "rag")
    _must_dir(API_SRC / "application" / "orchestration" / "evaluation")
    _must_dir(API_SRC / "application" / "policies")
    _must_dir(API_SRC / "application" / "services")
    _must_dir(API_SRC / "application" / "frontend_support")
    _must_dir(API_SRC / "application" / "http" / "wire")
    _must_dir(API_SRC / "infrastructure" / "auth")
    _must_dir(API_SRC / "infrastructure" / "persistence")
    _must_dir(API_SRC / "infrastructure" / "storage")
    _must_dir(API_SRC / "infrastructure" / "rag")
    _must_dir(API_SRC / "infrastructure" / "evaluation")
    _must_dir(API_SRC / "infrastructure" / "observability")
    _must_dir(API_SRC / "infrastructure" / "config")
    _must_dir(API_SRC / "composition")
    _must_dir(HTTP / "routers")
    _must_dir(HTTP / "schemas")


def test_interfaces_http_only_whitelisted_root_and_subdirs() -> None:
    """Routers/schemas only under their folders; no stray modules under interfaces/http/."""
    assert HTTP.is_dir(), "interfaces/http missing"
    for child in sorted(HTTP.iterdir()):
        name = child.name
        if name == "__pycache__":
            continue
        if child.is_dir():
            assert name in _HTTP_SUBDIRS, (
                f"Unexpected directory under interfaces/http: {name} "
                f"(allowed: {sorted(_HTTP_SUBDIRS)})"
            )
        else:
            assert name in _HTTP_ROOT_FILES, (
                f"Unexpected file under interfaces/http/: {name} "
                f"(allowed: {sorted(_HTTP_ROOT_FILES)})"
            )


def test_fastapi_routers_live_only_under_http_routers() -> None:
    """Any module that instantiates APIRouter must live under interfaces/http/routers/."""
    routers_dir = HTTP / "routers"
    offenders: list[str] = []
    for path in sorted(API_SRC.rglob("*.py")):
        if "__pycache__" in path.parts:
            continue
        text = path.read_text(encoding="utf-8")
        try:
            tree = ast.parse(text, filename=str(path))
        except SyntaxError:
            continue
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue
            func = node.func
            if isinstance(func, ast.Name) and func.id == "APIRouter":
                pass
            elif isinstance(func, ast.Attribute) and func.attr == "APIRouter":
                pass
            else:
                continue
            try:
                rel = path.relative_to(routers_dir)
            except ValueError:
                offenders.append(path.relative_to(REPO_ROOT).as_posix())
                break
    assert not offenders, (
        "APIRouter(...) must only appear under api/src/interfaces/http/routers/; "
        "offenders:\n  " + "\n  ".join(offenders)
    )


def test_fastapi_schemas_only_under_http_schemas() -> None:
    """
    Pydantic ``BaseModel`` / ``Field`` used for HTTP schemas should live under schemas/.

    We flag new subclass definitions of BaseModel outside schemas/ under interfaces/http.
    """
    schemas_dir = HTTP / "schemas"
    offenders: list[str] = []
    for path in sorted(HTTP.rglob("*.py")):
        if "__pycache__" in path.parts:
            continue
        if schemas_dir in path.parents or path.parent == schemas_dir:
            continue
        if path.name in _HTTP_ROOT_FILES:
            text = path.read_text(encoding="utf-8")
            if "BaseModel" not in text:
                continue
            try:
                tree = ast.parse(text, filename=str(path))
            except SyntaxError:
                continue
            for node in ast.walk(tree):
                if isinstance(node, ast.ClassDef):
                    for base in node.bases:
                        if isinstance(base, ast.Name) and base.id == "BaseModel":
                            offenders.append(path.relative_to(REPO_ROOT).as_posix())
                            break
                        if isinstance(base, ast.Attribute) and base.attr == "BaseModel":
                            offenders.append(path.relative_to(REPO_ROOT).as_posix())
                            break
    assert not offenders, (
        "BaseModel subclasses under interfaces/http must live in schemas/; offenders:\n  "
        + "\n  ".join(offenders)
    )


def test_composition_package_lives_under_api_src() -> None:
    root = API_SRC / "composition"
    _must_dir(root)
    assert not (API_SRC / "composition.py").is_file(), "composition must be a package, not a module"


def test_orchestration_code_lives_under_application_orchestration() -> None:
    """No nested ``orchestration`` package under use_cases (post-migration layout)."""
    uc = API_SRC / "application" / "use_cases"
    if not uc.is_dir():
        pytest.fail("application/use_cases missing")
    for p in uc.rglob("orchestration"):
        if p.is_dir():
            pytest.fail(
                f"Forbidden orchestration directory under use_cases: {p.relative_to(REPO_ROOT)}"
            )


def test_no_infrastructure_adapters_under_application() -> None:
    app = API_SRC / "application"
    for p in app.rglob("*"):
        if p.is_dir() and p.name == "adapters":
            pytest.fail(
                f"Forbidden adapters directory under application: {p.relative_to(REPO_ROOT)}"
            )


def test_docs_and_validation_scripts_present() -> None:
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


def test_frontend_entrypoint_and_layout_dirs() -> None:
    fe = REPO_ROOT / "frontend"
    src = fe / "src"
    _must_dir(fe)
    _must_dir(src / "pages")
    _must_dir(src / "components" / "shared")
    _must_dir(src / "state")
    _must_dir(src / "services")
    _must_dir(src / "utils")
    assert (fe / "app.py").is_file()


def test_no_streamlit_ui_trees_under_api_src() -> None:
    """UI pages and legacy ``ui`` packages belong under ``frontend/src``, not ``api/src``."""
    for rel in ("pages", "ui"):
        p = API_SRC / rel
        assert not p.exists(), f"Forbidden under api/src: {rel}/"


def test_no_backend_source_trees_copied_into_frontend_src() -> None:
    """Frontend must not vendor copies of backend layer packages (imports use PYTHONPATH)."""
    src = REPO_ROOT / "frontend" / "src"
    for name in ("domain", "application", "infrastructure", "composition", "interfaces"):
        p = src / name
        assert not p.exists(), f"Forbidden directory under frontend/src: {name}/"
