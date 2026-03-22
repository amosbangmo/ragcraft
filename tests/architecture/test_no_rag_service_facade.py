"""
Guardrails: no ``RAGService`` orchestration façade; container exposes chat use cases explicitly.
"""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
RAG_SERVICE_PATH = REPO_ROOT / "src" / "infrastructure" / "adapters" / "rag" / "rag_service.py"
APPLICATION_CONTAINER = REPO_ROOT / "src" / "composition" / "application_container.py"
RAG_ADAPTERS_ROOT = REPO_ROOT / "src" / "infrastructure" / "adapters" / "rag"


def _iter_py(root: Path) -> list[Path]:
    return sorted(p for p in root.rglob("*.py") if p.is_file() and "__pycache__" not in p.parts)


def test_rag_service_module_absent() -> None:
    assert not RAG_SERVICE_PATH.is_file(), (
        f"Remove legacy orchestration module {RAG_SERVICE_PATH.relative_to(REPO_ROOT)}; "
        "use BackendApplicationContainer chat use cases + chat_rag_wiring."
    )


def test_no_rag_service_class_in_src() -> None:
    hits: list[str] = []
    for path in _iter_py(REPO_ROOT / "src"):
        text = path.read_text(encoding="utf-8")
        if "class RAGService" in text:
            tree = ast.parse(text)
            for node in ast.walk(tree):
                if isinstance(node, ast.ClassDef) and node.name == "RAGService":
                    hits.append(str(path.relative_to(REPO_ROOT)))
    assert not hits, "RAGService class must not exist under src/:\n" + "\n".join(hits)


def test_backend_application_container_exposes_chat_rag_use_cases_not_rag_service() -> None:
    text = APPLICATION_CONTAINER.read_text(encoding="utf-8")
    normalized = text.replace("\r\n", "\n")
    assert "def chat_rag_use_cases" in text, "container should expose memoized chat_rag_use_cases"
    assert "def rag_service(" not in normalized, "container must not define rag_service(...)"


@pytest.mark.parametrize(
    "forbidden",
    [
        "BuildRagPipelineUseCase",
        "AskQuestionUseCase",
        "InspectRagPipelineUseCase",
        "PreviewSummaryRecallUseCase",
        "GenerateAnswerFromPipelineUseCase",
    ],
)
def test_rag_adapter_tree_does_not_import_chat_use_cases(forbidden: str) -> None:
    """Infrastructure RAG adapters must not construct or pull in chat use case classes."""
    offenders: list[str] = []
    for path in _iter_py(RAG_ADAPTERS_ROOT):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if not isinstance(node, ast.ImportFrom):
                continue
            mod = node.module or ""
            if not mod.startswith("src.application.use_cases.chat"):
                continue
            for alias in node.names:
                if alias.name == forbidden or alias.name.split(".")[-1] == forbidden:
                    offenders.append(f"{path.relative_to(REPO_ROOT)}: from {mod} import {alias.name}")
    assert not offenders, (
        f"RAG adapters must not import {forbidden} (orchestration belongs in application/composition):\n"
        + "\n".join(offenders)
    )
