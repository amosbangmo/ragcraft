"""
Architectural import-boundary guards (see ``tests/architecture/README.md``).
"""

from __future__ import annotations

from pathlib import Path

import pytest

from tests.architecture.import_scanner import any_module_matches, imported_top_level_modules, iter_python_files

REPO_ROOT = Path(__file__).resolve().parents[2]


@pytest.fixture(scope="module")
def domain_files() -> list[Path]:
    return iter_python_files(REPO_ROOT / "src" / "domain")


@pytest.fixture(scope="module")
def application_files() -> list[Path]:
    return iter_python_files(REPO_ROOT / "src" / "application")


@pytest.fixture(scope="module")
def infrastructure_files() -> list[Path]:
    return iter_python_files(REPO_ROOT / "src" / "infrastructure")


@pytest.fixture(scope="module")
def router_files() -> list[Path]:
    return iter_python_files(REPO_ROOT / "apps" / "api" / "routers")


@pytest.fixture(scope="module")
def composition_files() -> list[Path]:
    root = REPO_ROOT / "src" / "composition"
    return iter_python_files(root) if root.is_dir() else []


def test_domain_does_not_depend_on_outer_layers(domain_files: list[Path]) -> None:
    """
    Domain stays pure: business types and ports only.

    If this fails, you likely imported FastAPI/Streamlit/SQLite/LangChain or another outer layer.
    Move adapters to infrastructure/application and keep domain free of framework and I/O imports.
    """
    forbidden = (
        "src.infrastructure",
        "src.backend",
        "src.services",
        "src.application",
        "src.ui",
        "streamlit",
        "fastapi",
        "starlette",
        "sqlite3",
        "langchain",
        "apps",
    )
    violations: list[str] = []
    for path in domain_files:
        mods = imported_top_level_modules(path)
        bad = any_module_matches(mods, prefixes=forbidden)
        for m in bad:
            violations.append(f"{path.relative_to(REPO_ROOT)}: imports {m}")
    msg = (
        "Domain layer imported a forbidden module (presentation, HTTP, persistence drivers, or LangChain). "
        "Keep ports/DTOs here; wire frameworks only in application or infrastructure.\n"
    )
    assert not violations, msg + "\n".join(violations)


def test_application_does_not_depend_on_ui_or_infrastructure(application_files: list[Path]) -> None:
    """
    Application use cases must not depend on Streamlit or the API package.

    Only ``src.infrastructure.services`` is allowed among infrastructure imports.
    """
    violations: list[str] = []
    for path in application_files:
        mods = imported_top_level_modules(path)
        for mod in mods:
            if mod.startswith("streamlit") or mod == "streamlit":
                violations.append(f"{path.relative_to(REPO_ROOT)}: imports {mod}")
            elif mod.startswith("apps") or mod == "apps":
                violations.append(f"{path.relative_to(REPO_ROOT)}: imports {mod}")
            elif mod.startswith("src.infrastructure") and not mod.startswith("src.infrastructure.services"):
                violations.append(f"{path.relative_to(REPO_ROOT)}: imports {mod}")
    msg = (
        "Application layer must not import Streamlit, apps.api, or infrastructure adapters "
        "(except ``src.infrastructure.services``). Use ports/DTOs and the composition root instead.\n"
    )
    assert not violations, msg + "\n".join(violations)


def test_infrastructure_does_not_depend_on_application_or_streamlit(
    infrastructure_files: list[Path],
) -> None:
    """
    Core infrastructure (adapters, persistence, vector stores) must not call into ``src.application``.

    ``src/infrastructure/services`` hosts runtime services; those modules may import application
    use cases and DTOs by design.
    """
    violations: list[str] = []
    infra_root = REPO_ROOT / "src" / "infrastructure"
    services_root = infra_root / "services"
    for path in infrastructure_files:
        mods = imported_top_level_modules(path)
        try:
            under_services = services_root in path.parents or path.parent == services_root
        except ValueError:
            under_services = False
        if under_services:
            forbidden = ("apps",)
        else:
            forbidden = ("src.application", "streamlit", "apps")
        bad = any_module_matches(mods, prefixes=forbidden)
        for m in bad:
            violations.append(f"{path.relative_to(REPO_ROOT)}: imports {m}")
    msg = (
        "Non-service infrastructure must not import application use cases or Streamlit. "
        "Service modules under ``src/infrastructure/services`` may import ``src.application`` by design.\n"
    )
    assert not violations, msg + "\n".join(violations)


def test_api_routers_do_not_import_infrastructure(router_files: list[Path]) -> None:
    """
    Routers resolve use cases via FastAPI ``Depends`` on the composition root.

    Direct ``src.infrastructure`` imports bypass DI and couple HTTP to adapters; add a use case instead.
    """
    forbidden = ("src.infrastructure",)
    violations: list[str] = []
    for path in router_files:
        mods = imported_top_level_modules(path)
        bad = any_module_matches(mods, prefixes=forbidden)
        for m in bad:
            violations.append(f"{path.relative_to(REPO_ROOT)}: imports {m}")
    msg = "API routers must not import infrastructure packages; wire through apps.api.dependencies.\n"
    assert not violations, msg + "\n".join(violations)


def test_composition_root_avoids_streamlit(composition_files: list[Path]) -> None:
    if not composition_files:
        pytest.skip("no composition package")
    forbidden = ("streamlit", "apps")
    violations: list[str] = []
    for path in composition_files:
        mods = imported_top_level_modules(path)
        bad = any_module_matches(mods, prefixes=forbidden)
        for m in bad:
            violations.append(f"{path.relative_to(REPO_ROOT)}: imports {m}")
    assert not violations, "Composition root violations:\n" + "\n".join(violations)
