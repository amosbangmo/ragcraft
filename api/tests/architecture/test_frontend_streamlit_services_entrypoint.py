"""
Streamlit UI must reach the backend façade through :mod:`services.api_client` only.

``frontend/src/pages`` and ``frontend/src/components`` may import other ``services.*`` helpers
(streamlit auth, session context, DTOs, UI error mapping) but must not import transport/protocol
modules that bypass the canonical entrypoint.
"""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[3]
_PAGES = REPO_ROOT / "frontend" / "src" / "pages"
_COMPONENTS = REPO_ROOT / "frontend" / "src" / "components"

_ALLOWED_SERVICES_MODULES: frozenset[str] = frozenset(
    {
        "services.api_client",
        "services.ui_errors",
        "services.streamlit_context",
        "services.settings_dtos",
        "services.streamlit_auth",
    }
)


def _services_imports(py_file: Path) -> list[str]:
    tree = ast.parse(py_file.read_text(encoding="utf-8"), filename=str(py_file))
    out: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name == "services" or alias.name.startswith("services."):
                    out.append(alias.name)
        elif isinstance(node, ast.ImportFrom):
            if node.module is None:
                continue
            if node.module == "services":
                for alias in node.names:
                    if alias.name == "*":
                        out.append("services")
                    else:
                        out.append(f"services.{alias.name}")
            elif node.module.startswith("services."):
                out.append(node.module)
    return out


def _violations_for_root(root: Path) -> list[str]:
    bad: list[str] = []
    if not root.is_dir():
        return bad
    for path in sorted(root.rglob("*.py")):
        if not path.is_file():
            continue
        for mod in _services_imports(path):
            allowed = any(
                mod == a or mod.startswith(a + ".") for a in _ALLOWED_SERVICES_MODULES
            )
            if not allowed:
                rel = path.relative_to(REPO_ROOT)
                bad.append(f"{rel}: {mod}")
    return bad


@pytest.mark.architecture
def test_streamlit_pages_use_only_allowed_services_imports() -> None:
    v = _violations_for_root(_PAGES)
    assert not v, "Forbidden services import in pages:\n" + "\n".join(v)


@pytest.mark.architecture
def test_streamlit_components_use_only_allowed_services_imports() -> None:
    v = _violations_for_root(_COMPONENTS)
    assert not v, "Forbidden services import in components:\n" + "\n".join(v)
