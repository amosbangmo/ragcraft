"""Guardrail: Cypress scope doc stays present and lists canonical specs."""

from __future__ import annotations

from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[3]
_SCOPE = REPO_ROOT / "docs" / "cypress_scope.md"
_GEN = REPO_ROOT / "scripts" / "generate_artifacts.py"


@pytest.mark.architecture
def test_cypress_scope_doc_lists_streamlit_and_http_specs() -> None:
    text = _SCOPE.read_text(encoding="utf-8")
    assert "00_register_flow.cy.js" in text
    assert "09_workspace_http_journey.cy.js" in text
    assert "E2E_UI_JOURNEY_MAP" in text


@pytest.mark.architecture
def test_generate_artifacts_writes_journey_map() -> None:
    body = _GEN.read_text(encoding="utf-8")
    assert "E2E_UI_JOURNEY_MAP.txt" in body
    assert "00_register_flow.cy.js" in body
