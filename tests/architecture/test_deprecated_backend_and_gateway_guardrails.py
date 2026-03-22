"""
Extra import-level guardrails: deprecated ``src.backend`` shims and a thin ``src.frontend_gateway``.

See ``tests/architecture/README.md`` for the full boundary matrix.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from tests.architecture.import_scanner import collect_import_violations, imported_top_level_modules, iter_python_files

REPO_ROOT = Path(__file__).resolve().parents[2]


def test_src_production_tree_does_not_import_deprecated_backend_shims() -> None:
    """
    ``src/backend`` remains a compatibility re-export only.

    Production code under ``src/`` must import canonical modules (``src.infrastructure.services``, etc.),
    not ``src.backend.*``, so the legacy package cannot creep back as a runtime dependency.
    """
    src_root = REPO_ROOT / "src"
    backend_dir = src_root / "backend"
    violations: list[str] = []
    for path in iter_python_files(src_root):
        if path == backend_dir or backend_dir in path.parents:
            continue
        for mod in imported_top_level_modules(path):
            if mod == "src.backend" or mod.startswith("src.backend."):
                rel = path.relative_to(REPO_ROOT)
                violations.append(f"{rel}: imports {mod}")
    msg = (
        "Deprecated package ``src.backend`` must not be imported outside ``src/backend`` itself. "
        "Use ``src.infrastructure.services`` (or the composition root) as the canonical import path.\n"
    )
    assert not violations, msg + "\n".join(violations)


def test_frontend_gateway_does_not_import_infrastructure_internals() -> None:
    """
    The gateway sits between Streamlit and HTTP/in-process backends; it must not reach adapters
    (SQLite, FAISS, etc.) directly. Use ``src.application`` (+ allowed ``src.infrastructure.services``
    from application helpers such as ``frontend_support``) instead.
    """
    root = REPO_ROOT / "src" / "frontend_gateway"
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
    router_root = REPO_ROOT / "apps" / "api" / "routers"
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
