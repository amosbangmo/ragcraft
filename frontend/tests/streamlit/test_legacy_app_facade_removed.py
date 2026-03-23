"""Guardrails: Streamlit wiring must not reference the removed monolith app façade."""

from __future__ import annotations

from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[3]

# Historical qualified name; importing the factory must not load this module.
_LEGACY_MONOLITH_STREAMLIT_APP = "src.app.ragcraft_app"


@pytest.mark.parametrize(
    "relative_path",
    [
        Path("api") / "src" / "infrastructure" / "config" / "app_state.py",
        Path("api") / "src" / "application" / "frontend_support" / "streamlit_backend_factory.py",
    ],
)
def test_streamlit_runtime_modules_do_not_reference_removed_app_facade(relative_path: Path) -> None:
    text = (REPO_ROOT / relative_path).read_text(encoding="utf-8")
    assert "ragcraft_app" not in text
    assert "RAGCraftApp" not in text


def test_importing_streamlit_backend_factory_does_not_load_removed_app_module() -> None:
    import sys

    sys.modules.pop(_LEGACY_MONOLITH_STREAMLIT_APP, None)
    from application.frontend_support.streamlit_backend_factory import (  # noqa: F401
        build_streamlit_backend_application_container,
    )

    assert _LEGACY_MONOLITH_STREAMLIT_APP not in sys.modules
