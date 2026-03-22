"""Guardrails: production Streamlit wiring must not depend on the removed legacy ``src.app`` UI shell."""

from __future__ import annotations

from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]


@pytest.mark.parametrize(
    "relative_path",
    [
        Path("src") / "core" / "app_state.py",
        Path("src") / "frontend_gateway" / "in_process.py",
        Path("src") / "frontend_gateway" / "streamlit_backend_factory.py",
    ],
)
def test_streamlit_runtime_modules_do_not_reference_removed_app_facade(relative_path: Path) -> None:
    text = (REPO_ROOT / relative_path).read_text(encoding="utf-8")
    assert "ragcraft_app" not in text
    assert "RAGCraftApp" not in text


def test_importing_streamlit_backend_factory_does_not_load_removed_app_module() -> None:
    import sys

    sys.modules.pop("src.app.ragcraft_app", None)
    from src.frontend_gateway.streamlit_backend_factory import (  # noqa: F401
        build_streamlit_backend_application_container,
    )

    assert "src.app.ragcraft_app" not in sys.modules
