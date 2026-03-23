"""
Architecture guardrails for RAG orchestration boundaries (Clean Architecture migration).

These tests are intentionally static (AST / text) so they run without optional backend deps.
"""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[3]
COMPOSITION_DIR = REPO_ROOT / "api" / "src" / "composition"
ASSEMBLE_PIPELINE = (
    REPO_ROOT
    / "api"
    / "src"
    / "application"
    / "orchestration"
    / "rag"
    / "assemble_pipeline_from_recall.py"
)
POST_RECALL_PIPELINE_STEPS = (
    REPO_ROOT
    / "api"
    / "src"
    / "application"
    / "orchestration"
    / "rag"
    / "post_recall_pipeline_steps.py"
)
POST_RECALL_STAGE_ADAPTERS = (
    REPO_ROOT / "api" / "src" / "infrastructure" / "rag" / "post_recall_stage_adapters.py"
)

_MAX_ASSEMBLE_PIPELINE_LINES = 200
_MAX_POST_RECALL_PIPELINE_STEPS_LINES = 320
_MAX_POST_RECALL_ADAPTER_LINES = 280

_TRANSPORT_RAG_ADAPTER_MARKERS = (
    "from infrastructure.rag",
    "import infrastructure.rag",
)


def _iter_python_files(root: Path) -> list[Path]:
    return sorted(p for p in root.rglob("*.py") if "__pycache__" not in p.parts)


def _strip_docstrings_and_comments(source: str) -> str:
    """Rough filter so docstring mentions of banned paths do not false-positive import scans."""
    tree = ast.parse(source)
    lines = source.splitlines()

    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef, ast.Module)):
            if (
                node.body
                and isinstance(node.body[0], ast.Expr)
                and isinstance(node.body[0].value, ast.Constant)
                and isinstance(node.body[0].value.value, str)
            ):
                ds = node.body[0]
                for ln in range(ds.lineno - 1, ds.end_lineno):
                    if 0 <= ln < len(lines):
                        lines[ln] = ""
    return "\n".join(lines)


def _count_execute_calls_in_function(fn: ast.FunctionDef | ast.AsyncFunctionDef) -> int:
    count = 0
    for node in ast.walk(fn):
        if not isinstance(node, ast.Call):
            continue
        func = node.func
        if isinstance(func, ast.Attribute) and func.attr == "execute":
            count += 1
    return count


def _assert_no_application_use_case_imports(path: Path) -> None:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    offenders: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom):
            mod = node.module or ""
            if mod.startswith("application.use_cases") or mod == "application.use_cases":
                offenders.append(f"from {mod} import ...")
        elif isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name.startswith("application.use_cases"):
                    offenders.append(f"import {alias.name}")
    assert not offenders, (
        f"{path.relative_to(REPO_ROOT)} must not import application use_cases:\n"
        + "\n".join(offenders)
    )


@pytest.mark.parametrize(
    "transport_root",
    [
        REPO_ROOT / "api" / "src" / "interfaces" / "http",
        REPO_ROOT / "frontend" / "src" / "services",
    ],
    ids=["interfaces_http", "frontend_services"],
)
def test_transport_does_not_import_rag_orchestration_adapters(transport_root: Path) -> None:
    """Routers and ``frontend/src/services`` must use application use cases, not RAG infra modules."""
    assert transport_root.is_dir(), f"missing {transport_root}"
    violations: list[str] = []
    for path in _iter_python_files(transport_root):
        text = path.read_text(encoding="utf-8")
        filtered = _strip_docstrings_and_comments(text)
        for line in filtered.splitlines():
            stripped = line.strip()
            if stripped.startswith("#"):
                continue
            for marker in _TRANSPORT_RAG_ADAPTER_MARKERS:
                if marker in line:
                    violations.append(f"{path.relative_to(REPO_ROOT)}: {stripped}")
    assert not violations, "RAG adapter imports in transport layer:\n" + "\n".join(violations)


def test_composition_does_not_invoke_use_case_execute_except_chain_invalidation() -> None:
    """
    Composition wires objects; it must not sequence business flows via multiple ``execute`` calls.

    Allowed: ``BackendApplicationContainer.invalidate_project_chain`` → one administrative execute.
    """
    allowed_functions = frozenset({"invalidate_project_chain"})
    bad: list[str] = []
    for path in _iter_python_files(COMPOSITION_DIR):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                continue
            n_exec = _count_execute_calls_in_function(node)
            if n_exec == 0:
                continue
            if node.name in allowed_functions and n_exec == 1:
                continue
            bad.append(f"{path.name}:{node.name} has {n_exec} execute() call(s)")
    assert not bad, "Unexpected use-case execute usage in composition:\n" + "\n".join(bad)


def test_post_recall_stage_adapters_do_not_depend_on_use_cases() -> None:
    """Post-recall adapters are technical only; orchestration stays in application."""
    _assert_no_application_use_case_imports(POST_RECALL_STAGE_ADAPTERS)


def test_post_recall_stage_adapters_size_ratchet() -> None:
    """Fail if technical adapter module grows without splitting."""
    lines = POST_RECALL_STAGE_ADAPTERS.read_text(encoding="utf-8").splitlines()
    assert len(lines) <= _MAX_POST_RECALL_ADAPTER_LINES, (
        f"{POST_RECALL_STAGE_ADAPTERS.name} has {len(lines)} lines "
        f"(max {_MAX_POST_RECALL_ADAPTER_LINES}); split adapters into submodules"
    )


def test_assemble_pipeline_orchestration_lives_in_application() -> None:
    """Post-recall sequencing stays in application orchestration (coordinator + step module)."""
    coordinator = ASSEMBLE_PIPELINE.read_text(encoding="utf-8")
    steps = POST_RECALL_PIPELINE_STEPS.read_text(encoding="utf-8")
    combined = coordinator + steps
    for needle in (
        "stages.section_expansion.expand_section_pool",
        "stages.reranking.rerank_assets",
        "stages.prompt_render.build_answer_prompt",
    ):
        assert needle in combined, (
            f"expected orchestration step {needle!r} in post-recall orchestration"
        )
    assert "step_docstore_hydration" in coordinator
    assert "step_prompt_assembly" in coordinator
    assemble_lines = coordinator.splitlines()
    steps_lines = steps.splitlines()
    assert len(assemble_lines) <= _MAX_ASSEMBLE_PIPELINE_LINES, (
        f"assemble_pipeline_from_recall.py grew to {len(assemble_lines)} lines "
        f"(max {_MAX_ASSEMBLE_PIPELINE_LINES}); keep the coordinator thin"
    )
    assert len(steps_lines) <= _MAX_POST_RECALL_PIPELINE_STEPS_LINES, (
        f"post_recall_pipeline_steps.py grew to {len(steps_lines)} lines "
        f"(max {_MAX_POST_RECALL_PIPELINE_STEPS_LINES}); split post-recall steps"
    )
