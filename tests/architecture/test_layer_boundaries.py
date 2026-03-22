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
    forbidden = (
        "src.infrastructure",
        "src.backend",
        "src.services",
        "src.application",
        "streamlit",
        "apps",
    )
    violations: list[str] = []
    for path in domain_files:
        mods = imported_top_level_modules(path)
        bad = any_module_matches(mods, prefixes=forbidden)
        for m in bad:
            violations.append(f"{path.relative_to(REPO_ROOT)}: imports {m}")
    assert not violations, "Domain layer violations:\n" + "\n".join(violations)


def test_application_does_not_depend_on_ui_or_infrastructure(application_files: list[Path]) -> None:
    forbidden = (
        "streamlit",
        "apps",
        "src.infrastructure",
    )
    violations: list[str] = []
    for path in application_files:
        mods = imported_top_level_modules(path)
        bad = any_module_matches(mods, prefixes=forbidden)
        for m in bad:
            violations.append(f"{path.relative_to(REPO_ROOT)}: imports {m}")
    assert not violations, "Application layer violations:\n" + "\n".join(violations)


def test_infrastructure_does_not_depend_on_application_or_streamlit(
    infrastructure_files: list[Path],
) -> None:
    forbidden = (
        "src.application",
        "streamlit",
        "apps",
    )
    violations: list[str] = []
    for path in infrastructure_files:
        mods = imported_top_level_modules(path)
        bad = any_module_matches(mods, prefixes=forbidden)
        for m in bad:
            violations.append(f"{path.relative_to(REPO_ROOT)}: imports {m}")
    assert not violations, "Infrastructure layer violations:\n" + "\n".join(violations)


def test_api_routers_do_not_import_infrastructure(router_files: list[Path]) -> None:
    """HTTP adapters wire use cases via ``Depends``; they must not reach SQLite/FAISS modules directly."""
    forbidden = ("src.infrastructure",)
    violations: list[str] = []
    for path in router_files:
        mods = imported_top_level_modules(path)
        bad = any_module_matches(mods, prefixes=forbidden)
        for m in bad:
            violations.append(f"{path.relative_to(REPO_ROOT)}: imports {m}")
    assert not violations, "API router violations:\n" + "\n".join(violations)


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
