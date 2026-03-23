"""Chat RAG use cases depend on explicit domain ports (retrieval, generation, query log)."""

from __future__ import annotations

from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[3]


@pytest.mark.parametrize(
    "relative_path,expected_substrings",
    [
        (
            Path("api") / "src" / "application" / "use_cases" / "chat" / "ask_question.py",
            ("RetrievalPort", "GenerationPort", "QueryLogPort"),
        ),
        (
            Path("api") / "src" / "application" / "use_cases" / "chat" / "inspect_rag_pipeline.py",
            ("RetrievalPort",),
        ),
        (
            Path("api")
            / "src"
            / "application"
            / "use_cases"
            / "chat"
            / "generate_answer_from_pipeline.py",
            ("GenerationPort",),
        ),
    ],
)
def test_rag_use_case_modules_reference_boundary_ports(
    relative_path: Path, expected_substrings: tuple[str, ...]
) -> None:
    text = (REPO_ROOT / relative_path).read_text(encoding="utf-8")
    for s in expected_substrings:
        assert s in text, f"{relative_path} should reference {s} for port/adapters boundaries"
