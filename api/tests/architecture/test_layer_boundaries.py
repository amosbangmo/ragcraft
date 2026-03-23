"""
Infrastructure and composition import guards.

Domain, application, and HTTP-router rules live in :mod:`architecture.test_layer_import_rules`.
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


@pytest.fixture(scope="module")
def infrastructure_files() -> list[Path]:
    return iter_python_files(REPO_ROOT / "api" / "src" / "infrastructure")


@pytest.fixture(scope="module")
def composition_files() -> list[Path]:
    root = REPO_ROOT / "api" / "src" / "composition"
    return iter_python_files(root) if root.is_dir() else []


def test_infrastructure_does_not_depend_on_application_or_streamlit(
    infrastructure_files: list[Path],
) -> None:
    """
    Core infrastructure (persistence, vector stores outside ``adapters/``) must not call into
    ``src.application`` or Streamlit.

    Adapter modules under ``src/infrastructure/adapters`` are checked separately for ``apps`` only here;
    they must not import ``src.application`` at all (see ``test_adapter_application_imports.py``).
    """
    violations: list[str] = []
    infra_root = REPO_ROOT / "api" / "src" / "infrastructure"
    adapters_root = infra_root / "adapters"
    streamlit_shims = {
        (infra_root / "auth" / "auth_service.py").resolve(),
        (infra_root / "auth" / "guards.py").resolve(),
        (infra_root / "config" / "app_state.py").resolve(),
        (infra_root / "config" / "session.py").resolve(),
    }
    for path in infrastructure_files:
        if path.resolve() in streamlit_shims:
            continue
        try:
            rel = path.relative_to(infra_root)
        except ValueError:
            rel = None
        if rel is not None and rel.parts[0] == "auth" and rel.name == "auth_credentials.py":
            continue
        mods = imported_top_level_modules(path)
        try:
            under_adapters = adapters_root in path.parents or path.parent == adapters_root
        except ValueError:
            under_adapters = False
        if under_adapters:
            forbidden = ("apps",)
        else:
            forbidden = ("application", "streamlit", "apps")
        bad = any_module_matches(mods, prefixes=forbidden)
        for m in bad:
            violations.append(f"{path.relative_to(REPO_ROOT)}: imports {m}")
    msg = (
        "Non-adapter infrastructure must not import application use cases or Streamlit. "
        "Adapter modules under ``src/infrastructure/adapters`` must not import ``src.application`` "
        "(see ``test_adapter_application_imports.py``).\n"
    )
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
