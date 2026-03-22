"""
Architecture guardrails for RAG orchestration boundaries (Clean Architecture migration).

These tests are intentionally static (AST / text) so they run without optional backend deps.
"""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
COMPOSITION_DIR = REPO_ROOT / "src" / "composition"
PIPELINE_ASSEMBLY = REPO_ROOT / "src" / "infrastructure" / "adapters" / "rag" / "pipeline_assembly_service.py"
RAG_SERVICE = REPO_ROOT / "src" / "infrastructure" / "adapters" / "rag" / "rag_service.py"

# Ratchet: assembly service is a known hotspot; fail if it grows unbounded without splitting.
_MAX_PIPELINE_ASSEMBLY_LINES = 450

_TRANSPORT_RAG_ADAPTER_MARKERS = (
    "from src.infrastructure.adapters.rag",
    "import src.infrastructure.adapters.rag",
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


@pytest.mark.parametrize(
    "transport_root",
    [
        REPO_ROOT / "apps" / "api",
        REPO_ROOT / "src" / "frontend_gateway",
    ],
    ids=["apps_api", "frontend_gateway"],
)
def test_transport_does_not_import_rag_orchestration_adapters(transport_root: Path) -> None:
    """Routers and gateway must use application use cases, not RAG adapter modules."""
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


def test_pipeline_assembly_service_does_not_depend_on_use_cases() -> None:
    """Adapter implements PipelineAssemblyPort only; orchestration ownership stays in application layer."""
    tree = ast.parse(PIPELINE_ASSEMBLY.read_text(encoding="utf-8"))
    offenders: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom):
            mod = node.module or ""
            if mod.startswith("src.application.use_cases") or mod == "src.application.use_cases":
                offenders.append(f"from {mod} import ...")
        elif isinstance(node, ast.Import):
            for alias in node.names:
                name = alias.name
                if name.startswith("src.application.use_cases"):
                    offenders.append(f"import {name}")
    assert not offenders, (
        f"{PIPELINE_ASSEMBLY.relative_to(REPO_ROOT)} must not import application use_cases:\n"
        + "\n".join(offenders)
    )


def test_pipeline_assembly_service_size_ratchet() -> None:
    """Fail if the god-object grows without an intentional split (see module TODO)."""
    lines = PIPELINE_ASSEMBLY.read_text(encoding="utf-8").splitlines()
    assert len(lines) <= _MAX_PIPELINE_ASSEMBLY_LINES, (
        f"{PIPELINE_ASSEMBLY.name} has {len(lines)} lines (max {_MAX_PIPELINE_ASSEMBLY_LINES}); "
        "split into src/infrastructure/adapters/rag/pipeline_assembly/ per module docstring"
    )


def test_rag_service_facade_must_not_construct_use_cases_if_present() -> None:
    """Legacy compatibility module, if added back, must not own orchestration or construct use cases."""
    if not RAG_SERVICE.is_file():
        return
    tree = ast.parse(RAG_SERVICE.read_text(encoding="utf-8"))
    offenders: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom):
            mod = node.module or ""
            if mod.startswith("src.application.use_cases") or mod == "src.application.use_cases":
                offenders.append(f"from {mod} import ...")
        elif isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name.startswith("src.application.use_cases"):
                    offenders.append(f"import {alias.name}")
    assert not offenders, (
        f"{RAG_SERVICE.relative_to(REPO_ROOT)} must not import use_cases "
        "(compatibility façade delegates to BackendApplicationContainer / use cases only):\n"
        + "\n".join(offenders)
    )
