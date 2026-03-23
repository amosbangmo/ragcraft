"""The legacy Streamlit shell module under ``src.app`` must not return to the repository."""

from __future__ import annotations

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]


def test_legacy_app_wrapper_py_not_present() -> None:
    legacy = REPO_ROOT / "api" / "src" / "app" / "ragcraft_app.py"
    assert not legacy.is_file(), (
        f"Legacy UI wrapper must stay removed; delete if reintroduced: {legacy.as_posix()}"
    )
