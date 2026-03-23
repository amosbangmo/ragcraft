"""
Import-level guardrails: forbidden monolith Python roots (``src.*``, ``apps.*`` shims), removed
``api/src/infrastructure/services``, and stray packages under ``api/src`` (``adapters``, ``backend``, ``services``).

See ``api/tests/architecture/README.md`` for the full boundary matrix.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from architecture.import_scanner import imported_top_level_modules, iter_python_files

REPO_ROOT = Path(__file__).resolve().parents[3]


def _repo_python_paths_for_legacy_shim_import_guards() -> list[Path]:
    """Trees scanned so removed shim packages cannot be reintroduced via imports."""
    paths: list[Path] = []
    for sub in ("api/src", "frontend/src", "api/tests", "frontend/tests"):
        root = REPO_ROOT.joinpath(*sub.split("/"))
        if root.is_dir():
            paths.extend(iter_python_files(root))
    for legacy in ("src", "apps", "pages", "tests"):
        root = REPO_ROOT / legacy
        if root.is_dir():
            paths.extend(iter_python_files(root))
    streamlit_entry = REPO_ROOT / "frontend" / "app.py"
    if streamlit_entry.is_file():
        paths.append(streamlit_entry)
    return paths


def test_legacy_src_adapters_package_directory_is_absent() -> None:
    """``api/src/adapters`` must not exist (implementations live under ``api/src/infrastructure/``)."""
    adapters_dir = REPO_ROOT / "api" / "src" / "adapters"
    assert not adapters_dir.exists(), (
        "Remove stray api/src/adapters/; port implementations belong under api/src/infrastructure/. "
        f"Found: {adapters_dir}"
    )


def test_legacy_backend_package_directory_is_absent() -> None:
    """``api/src/backend`` shim directory must not return."""
    backend_dir = REPO_ROOT / "api" / "src" / "backend"
    assert not backend_dir.exists(), (
        "Remove api/src/backend/; use api/src/application and api/src/infrastructure with composition. "
        f"Found: {backend_dir}"
    )


def test_legacy_src_services_package_directory_is_absent() -> None:
    """``api/src/services`` must not exist (orchestration is ``application``; IO is ``infrastructure``)."""
    services_dir = REPO_ROOT / "api" / "src" / "services"
    assert not services_dir.exists(), (
        "Remove api/src/services/; use api/src/application and api/src/infrastructure/. "
        f"Found: {services_dir}"
    )


def test_legacy_infrastructure_services_package_directory_is_absent() -> None:
    """``api/src/infrastructure/services`` package must not return."""
    services_dir = REPO_ROOT / "api" / "src" / "infrastructure" / "services"
    assert not services_dir.exists(), (
        "Remove api/src/infrastructure/services/; use concrete modules under api/src/infrastructure/. "
        f"Found: {services_dir}"
    )


def test_src_tree_does_not_import_legacy_adapters_package() -> None:
    """No module under ``api/src`` may import the removed monolith package ``src.adapters``."""
    src_root = REPO_ROOT / "api" / "src"
    violations: list[str] = []
    for path in iter_python_files(src_root):
        for mod in imported_top_level_modules(path):
            if mod == "src.adapters" or mod.startswith("src.adapters."):
                rel = path.relative_to(REPO_ROOT)
                violations.append(f"{rel}: imports {mod}")
    msg = "Monolith import ``src.adapters`` is forbidden; use ``infrastructure`` modules under api/src/.\n"
    assert not violations, msg + "\n".join(violations)


def test_codebase_python_does_not_import_removed_backend_package() -> None:
    """No code may import the removed monolith package ``src.backend``."""
    violations: list[str] = []
    for path in _repo_python_paths_for_legacy_shim_import_guards():
        for mod in imported_top_level_modules(path):
            if mod == "src.backend" or mod.startswith("src.backend."):
                rel = path.relative_to(REPO_ROOT)
                violations.append(f"{rel}: imports {mod}")
    msg = "Monolith import ``src.backend`` is forbidden; use ``application``, ``infrastructure``, ``composition``.\n"
    assert not violations, msg + "\n".join(violations)


def test_codebase_python_does_not_import_removed_infrastructure_services_package() -> None:
    """No imports of ``infrastructure.services`` (removed package name)."""
    violations: list[str] = []
    for path in _repo_python_paths_for_legacy_shim_import_guards():
        for mod in imported_top_level_modules(path):
            if mod == "infrastructure.services" or mod.startswith("infrastructure.services."):
                rel = path.relative_to(REPO_ROOT)
                violations.append(f"{rel}: imports {mod}")
    msg = (
        "``infrastructure.services`` was removed; use modules under api/src/infrastructure/ and "
        "``application`` for orchestration.\n"
    )
    assert not violations, msg + "\n".join(violations)


def test_codebase_python_does_not_import_removed_src_services_package() -> None:
    """No imports of ``src.services`` (removed monolith package)."""
    violations: list[str] = []
    for path in _repo_python_paths_for_legacy_shim_import_guards():
        for mod in imported_top_level_modules(path):
            if mod == "src.services" or mod.startswith("src.services."):
                rel = path.relative_to(REPO_ROOT)
                violations.append(f"{rel}: imports {mod}")
    msg = (
        "Monolith import ``src.services`` is forbidden; use ``application`` and ``infrastructure`` under api/src/.\n"
    )
    assert not violations, msg + "\n".join(violations)


def test_frontend_services_infrastructure_imports_are_limited() -> None:
    """
    Gateway code lives under ``frontend/src/services``; it may use ``infrastructure.config`` and
    ``infrastructure.auth`` only — not adapters, persistence, RAG, or vector stores.
    """
    root = REPO_ROOT / "frontend" / "src" / "services"
    violations: list[str] = []
    if root.is_dir():
        for path in iter_python_files(root):
            for mod in imported_top_level_modules(path):
                if not (mod == "infrastructure" or mod.startswith("infrastructure.")):
                    continue
                if mod == "infrastructure.config" or mod.startswith("infrastructure.config."):
                    continue
                if mod == "infrastructure.auth" or mod.startswith("infrastructure.auth."):
                    continue
                violations.append(f"{path.relative_to(REPO_ROOT)}: imports {mod}")
    msg = (
        "frontend/src/services may import only infrastructure.config.* and infrastructure.auth.*.\n"
    )
    assert not violations, msg + "\n".join(violations)


def test_api_routers_do_not_instantiate_core_services_inline() -> None:
    """
    Lightweight structural check: routers should not construct ``RAGService`` / ``EvaluationService``
    directly (bypasses ``BackendApplicationContainer`` and ``interfaces.http.dependencies``).
    """
    router_root = REPO_ROOT / "api" / "src" / "interfaces" / "http" / "routers"
    if not router_root.is_dir():
        pytest.skip("no API routers package")
    needles = ("RAGService(", "EvaluationService(", "VectorStoreService(", "DocStoreService(")
    hits: list[str] = []
    for path in sorted(router_root.rglob("*.py")):
        if not path.is_file():
            continue
        text = path.read_text(encoding="utf-8")
        for line_no, line in enumerate(text.splitlines(), start=1):
            stripped = line.strip()
            if stripped.startswith("#"):
                continue
            for n in needles:
                if n in line:
                    rel = path.relative_to(REPO_ROOT)
                    hits.append(f"{rel}:{line_no}: contains `{n}`")
    msg = (
        "API routers should obtain services only via FastAPI dependencies (composition root), "
        "not by instantiating infrastructure service classes inline.\n"
    )
    assert not hits, msg + "\n".join(hits)
