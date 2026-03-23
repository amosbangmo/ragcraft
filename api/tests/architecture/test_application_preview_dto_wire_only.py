"""Summary-recall preview DTO stays typed; JSON lives in wire mappers only."""

from __future__ import annotations

from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[3]
_PREVIEW = (
    REPO_ROOT / "api" / "src" / "application" / "common" / "summary_recall_preview.py"
)


@pytest.mark.architecture
def test_summary_recall_preview_dto_has_no_to_dict() -> None:
    text = _PREVIEW.read_text(encoding="utf-8")
    assert "def to_dict" not in text
    assert "legacy dict" not in text.lower()
