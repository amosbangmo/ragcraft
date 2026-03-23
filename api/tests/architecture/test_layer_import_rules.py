"""
Blocking import-boundary rules (PROMPT 2).

Complements :mod:`architecture.test_layer_boundaries` with strict, layout-aligned checks.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from architecture.import_scanner import (
    any_module_matches,
    imported_top_level_modules,
    iter_python_files,
)

REPO_ROOT = Path(__file__).resolve().parents[3]


def _violations_for_forbidden(
    paths: list[Path],
    *,
    forbidden: tuple[str, ...],
) -> list[str]:
    out: list[str] = []
    for path in paths:
        mods = imported_top_level_modules(path)
        bad = any_module_matches(mods, prefixes=forbidden)
        for m in bad:
            out.append(f"{path.relative_to(REPO_ROOT)}: imports {m}")
    return out


def _config_only_infrastructure_import(mod: str) -> bool:
    """Allow only ``infrastructure.config`` (paths/constants), not adapters or services."""
    if mod == "infrastructure" or mod.startswith("infrastructure."):
        return not (mod == "infrastructure.config" or mod.startswith("infrastructure.config."))
    return False


@pytest.fixture(scope="module")
def domain_files() -> list[Path]:
    return iter_python_files(REPO_ROOT / "api" / "src" / "domain")


@pytest.fixture(scope="module")
def application_files() -> list[Path]:
    return iter_python_files(REPO_ROOT / "api" / "src" / "application")


@pytest.fixture(scope="module")
def router_files() -> list[Path]:
    return iter_python_files(REPO_ROOT / "api" / "src" / "interfaces" / "http" / "routers")


def test_domain_imports_stay_inner_layer(domain_files: list[Path]) -> None:
    forbidden = (
        "fastapi",
        "starlette",
        "streamlit",
        "sqlite3",
        "langchain",
        "interfaces",
        "composition",
        "src.infrastructure",
        "src.application",
        "src.backend",
        "src.services",
        "src.ui",
        "apps",
    )
    v = _violations_for_forbidden(domain_files, forbidden=forbidden)
    extra: list[str] = []
    for path in domain_files:
        mods = imported_top_level_modules(path)
        for mod in mods:
            if _config_only_infrastructure_import(mod):
                extra.append(f"{path.relative_to(REPO_ROOT)}: imports {mod}")
    assert not extra, (
        "Domain must not import concrete infrastructure (allowed exception: ``infrastructure.config`` only).\n"
        + "\n".join(extra)
    )
    assert not v, "Domain must not depend on transport or composition.\n" + "\n".join(v)


def test_application_avoids_transport_and_concrete_infrastructure(
    application_files: list[Path],
) -> None:
    violations: list[str] = []
    for path in application_files:
        mods = imported_top_level_modules(path)
        for mod in mods:
            if mod.startswith("fastapi") or mod == "fastapi":
                violations.append(f"{path.relative_to(REPO_ROOT)}: imports {mod}")
            elif mod.startswith("starlette") or mod == "starlette":
                violations.append(f"{path.relative_to(REPO_ROOT)}: imports {mod}")
            elif mod.startswith("streamlit") or mod == "streamlit":
                violations.append(f"{path.relative_to(REPO_ROOT)}: imports {mod}")
            elif mod.startswith("interfaces") or mod == "interfaces":
                violations.append(f"{path.relative_to(REPO_ROOT)}: imports {mod}")
            elif _config_only_infrastructure_import(mod):
                violations.append(f"{path.relative_to(REPO_ROOT)}: imports {mod}")
    assert not violations, (
        "Application use cases must not import FastAPI/Starlette/Streamlit/interfaces or "
        "concrete infrastructure (allowed exception: ``infrastructure.config`` only).\n"
        + "\n".join(violations)
    )


def test_http_routers_do_not_import_infrastructure(router_files: list[Path]) -> None:
    violations: list[str] = []
    for path in router_files:
        mods = imported_top_level_modules(path)
        for mod in mods:
            if mod == "infrastructure" or mod.startswith("infrastructure."):
                violations.append(f"{path.relative_to(REPO_ROOT)}: imports {mod}")
    assert not violations, (
        "HTTP routers must not import infrastructure (even config); wire via dependencies / use cases.\n"
        + "\n".join(violations)
    )
