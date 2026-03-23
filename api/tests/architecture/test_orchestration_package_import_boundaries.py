"""
Orchestration-heavy application subtrees must stay free of infrastructure and delivery imports.

Complements :mod:`architecture.test_layer_boundaries` and
:mod:`architecture.test_application_orchestration_purity` by scoping **folders** where
regressions would most damage the architecture (RAG chat orchestration, evaluation flows).
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

_ORCHESTRATION_ROOTS: tuple[Path, ...] = (
    REPO_ROOT / "api" / "src" / "application" / "orchestration" / "rag",
    REPO_ROOT / "api" / "src" / "application" / "orchestration" / "evaluation",
    REPO_ROOT / "api" / "src" / "application" / "use_cases" / "evaluation",
    REPO_ROOT / "api" / "src" / "application" / "rag",
)

_FORBIDDEN = (
    "infrastructure",
    "fastapi",
    "starlette",
    "streamlit",
    "uvicorn",
    "langchain",
    "langgraph",
    "faiss",
    "sqlite3",
)


@pytest.fixture(scope="module")
def orchestration_python_files() -> list[Path]:
    files: list[Path] = []
    for root in _ORCHESTRATION_ROOTS:
        if root.is_dir():
            files.extend(iter_python_files(root))
    return files


def test_orchestration_packages_avoid_infrastructure_and_delivery_tech(
    orchestration_python_files: list[Path],
) -> None:
    if not orchestration_python_files:
        pytest.skip("no orchestration package files found")
    violations: list[str] = []
    for path in orchestration_python_files:
        mods = imported_top_level_modules(path)
        bad = any_module_matches(mods, prefixes=_FORBIDDEN)
        for m in bad:
            violations.append(f"{path.relative_to(REPO_ROOT)}: imports {m}")
    assert not violations, (
        "Orchestration subtrees and application RAG DTOs must not import the ``infrastructure`` "
        "package or HTTP/Streamlit/LLM runtime stacks. Use domain ports and application "
        "collaborators only.\n" + "\n".join(violations)
    )
