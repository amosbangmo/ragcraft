"""
Repo-wide frontend layout and thin-page import rules (runs in the API test suite).

``frontend/src/services`` may import backend packages for the in-process gateway; pages and
components must stay on the façade (see ``docs/dependency_rules.md``).

Streamlit multipage modules live under ``frontend/pages/`` (next to ``app.py``); shared UI code
under ``frontend/src/`` remains on ``PYTHONPATH`` for ``components``, ``services``, etc.
"""

from __future__ import annotations

from pathlib import Path

from architecture.import_scanner import (
    collect_import_violations,
    imported_top_level_modules,
    iter_python_files,
)

REPO_ROOT = Path(__file__).resolve().parents[3]
FRONTEND_SRC = REPO_ROOT / "frontend" / "src"
FRONTEND_PAGES = REPO_ROOT / "frontend" / "pages"


def test_required_frontend_directories_exist() -> None:
    for p in (
        FRONTEND_SRC,
        FRONTEND_PAGES,
        FRONTEND_SRC / "services",
        FRONTEND_SRC / "components",
    ):
        assert p.is_dir(), f"Missing {p.relative_to(REPO_ROOT)}"


def test_pages_and_components_avoid_composition_and_use_cases() -> None:
    roots = [FRONTEND_PAGES, FRONTEND_SRC / "components"]
    violations = collect_import_violations(
        roots,
        forbidden=(
            "composition",
            "application.use_cases",
            "application.orchestration",
            "interfaces",
        ),
        repo_root=REPO_ROOT,
    )
    assert not violations, (
        "Streamlit pages/components must not import composition, application orchestration/use_cases, "
        "or interfaces.http directly.\n" + "\n".join(violations)
    )


def test_pages_and_components_avoid_domain_and_application_except_documented_shims() -> None:
    """
    UI surfaces use gateway services; they must not import ``domain`` or ``application`` packages.

    **Narrow exception:** none — auth for pages uses ``infrastructure.auth.guards`` only.
    """
    violations: list[str] = []
    for root in (FRONTEND_PAGES, FRONTEND_SRC / "components"):
        if not root.is_dir():
            continue
        for path in iter_python_files(root):
            mods = imported_top_level_modules(path)
            for mod in mods:
                if mod == "domain" or mod.startswith("domain."):
                    violations.append(f"{path.relative_to(REPO_ROOT)}: imports {mod}")
                if mod == "application" or mod.startswith("application."):
                    violations.append(f"{path.relative_to(REPO_ROOT)}: imports {mod}")
    assert not violations, "Pages/components must not import domain or application.\n" + "\n".join(
        violations
    )


def test_pages_and_components_infrastructure_limited_to_auth_guards() -> None:
    """Allow only ``infrastructure.auth`` imports in pages/components (session guards)."""
    violations: list[str] = []
    for root in (FRONTEND_PAGES, FRONTEND_SRC / "components"):
        if not root.is_dir():
            continue
        for path in iter_python_files(root):
            mods = imported_top_level_modules(path)
            for mod in mods:
                if not (mod == "infrastructure" or mod.startswith("infrastructure.")):
                    continue
                if mod == "infrastructure.auth" or mod.startswith("infrastructure.auth."):
                    continue
                violations.append(f"{path.relative_to(REPO_ROOT)}: imports {mod}")
    assert not violations, (
        "Pages/components may import only infrastructure.auth.* (not full infra stack).\n"
        + "\n".join(violations)
    )
