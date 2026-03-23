"""
Extra import-level guardrails: removed legacy packages (``src.backend``, ``src.adapters``,
``infrastructure.services``) and a thin ``src.frontend_gateway``.

See ``tests/architecture/README.md`` for the full boundary matrix.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from architecture.import_scanner import collect_import_violations, imported_top_level_modules, iter_python_files

REPO_ROOT = Path(__file__).resolve().parents[3]


def _repo_python_paths_for_legacy_shim_import_guards() -> list[Path]:
    """Trees scanned so removed shim packages cannot be reintroduced via imports."""
    paths: list[Path] = []
    for sub in ("src", "apps", "pages", "tests"):
        root = REPO_ROOT / sub
        if root.is_dir():
            paths.extend(iter_python_files(root))
    streamlit_entry = REPO_ROOT / "streamlit_app.py"
    if streamlit_entry.is_file():
        paths.append(streamlit_entry)
    return paths


def test_legacy_src_adapters_package_directory_is_absent() -> None:
    """The old ``src/adapters`` tree was folded into ``src/infrastructure/adapters`` (e.g. sqlite)."""
    adapters_dir = REPO_ROOT / "api" / "src" / "adapters"
    assert not adapters_dir.exists(), (
        "``src/adapters`` was removed; SQLite and other port implementations live under "
        f"``src/infrastructure/adapters``. Remove leftover directory: {adapters_dir}"
    )


def test_legacy_backend_package_directory_is_absent() -> None:
    """The removed shim tree ``src/backend`` must not exist (canonical code lives under ``infrastructure.adapters``)."""
    backend_dir = REPO_ROOT / "api" / "src" / "backend"
    assert not backend_dir.exists(), (
        "``src/backend`` was removed; use ``infrastructure.adapters`` and application use cases. "
        f"Delete leftover directory: {backend_dir}"
    )


def test_legacy_src_services_package_directory_is_absent() -> None:
    """The legacy ``src/services`` layer was removed; use ``src.application`` and ``infrastructure.adapters``."""
    services_dir = REPO_ROOT / "api" / "src" / "services"
    assert not services_dir.exists(), (
        "``src/services`` was removed; put orchestration in ``src.application`` and technical code in "
        f"``src/infrastructure/adapters``. Delete leftover directory: {services_dir}"
    )


def test_legacy_infrastructure_services_package_directory_is_absent() -> None:
    """
    The old ``src/infrastructure/services`` package was removed; runtime code lives in
    ``src/infrastructure/adapters/`` (and use cases in ``src/application/``).
    """
    services_dir = REPO_ROOT / "api" / "src" / "infrastructure" / "services"
    assert not services_dir.exists(), (
        "``src/infrastructure/services`` was removed; put concrete code in "
        "``src/infrastructure/adapters`` and orchestration in ``src/application``. "
        f"Delete leftover directory: {services_dir}"
    )


def test_src_tree_does_not_import_legacy_adapters_package() -> None:
    """No module under ``src/`` may import ``src.adapters`` (package removed; use ``infrastructure.adapters``)."""
    src_root = REPO_ROOT / "src"
    violations: list[str] = []
    for path in iter_python_files(src_root):
        for mod in imported_top_level_modules(path):
            if mod == "src.adapters" or mod.startswith("src.adapters."):
                rel = path.relative_to(REPO_ROOT)
                violations.append(f"{rel}: imports {mod}")
    msg = (
        "``src.adapters`` was removed. Import concrete adapters from ``infrastructure.adapters``.\n"
    )
    assert not violations, msg + "\n".join(violations)


def test_codebase_python_does_not_import_removed_backend_package() -> None:
    """
    No Python under ``src/``, ``apps/``, ``pages/``, ``tests/``, or the Streamlit shell may import
    ``src.backend`` (shim package removed — use application use cases, ``infrastructure.adapters``,
    and ``src.composition``).
    """
    violations: list[str] = []
    for path in _repo_python_paths_for_legacy_shim_import_guards():
        for mod in imported_top_level_modules(path):
            if mod == "src.backend" or mod.startswith("src.backend."):
                rel = path.relative_to(REPO_ROOT)
                violations.append(f"{rel}: imports {mod}")
    msg = (
        "``src.backend`` was removed. Use ``infrastructure.adapters`` (or the composition root).\n"
    )
    assert not violations, msg + "\n".join(violations)


def test_codebase_python_does_not_import_removed_infrastructure_services_package() -> None:
    """No imports of ``infrastructure.services`` (removed — use ``infrastructure.adapters`` / application)."""
    violations: list[str] = []
    for path in _repo_python_paths_for_legacy_shim_import_guards():
        for mod in imported_top_level_modules(path):
            if mod == "infrastructure.services" or mod.startswith("infrastructure.services."):
                rel = path.relative_to(REPO_ROOT)
                violations.append(f"{rel}: imports {mod}")
    msg = (
        "``infrastructure.services`` was removed. Use ``infrastructure.adapters`` "
        "for concrete adapters and ``src.application`` for orchestration.\n"
    )
    assert not violations, msg + "\n".join(violations)


def test_codebase_python_does_not_import_removed_src_services_package() -> None:
    """No imports of ``src.services`` (removed — use ``src.application`` / ``infrastructure.adapters``)."""
    violations: list[str] = []
    for path in _repo_python_paths_for_legacy_shim_import_guards():
        for mod in imported_top_level_modules(path):
            if mod == "src.services" or mod.startswith("src.services."):
                rel = path.relative_to(REPO_ROOT)
                violations.append(f"{rel}: imports {mod}")
    msg = (
        "``src.services`` was removed. Use ``src.application`` for orchestration and "
        "``infrastructure.adapters`` for concrete adapters.\n"
    )
    assert not violations, msg + "\n".join(violations)


def test_frontend_gateway_does_not_import_infrastructure_internals() -> None:
    """
    The gateway sits between Streamlit and HTTP/in-process backends; it must not reach adapters
    (SQLite, FAISS, etc.) directly. Use ``src.application`` (+ allowed ``infrastructure.adapters``
    from application helpers such as ``frontend_support``) instead.
    """
    root = REPO_ROOT / "api" / "src" / "frontend_gateway"
    violations = collect_import_violations([root], forbidden=("src.infrastructure",), repo_root=REPO_ROOT)
    msg = (
        "``src.frontend_gateway`` must not import ``src.infrastructure`` (any submodule). "
        "Keep transport/protocol code here; depend on application-layer factories for service stubs.\n"
    )
    assert not violations, msg + "\n".join(violations)


def test_api_routers_do_not_instantiate_core_services_inline() -> None:
    """
    Lightweight structural check: routers should not construct ``RAGService`` / ``EvaluationService``
    directly (bypasses ``BackendApplicationContainer`` and ``apps.api.dependencies``).
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
