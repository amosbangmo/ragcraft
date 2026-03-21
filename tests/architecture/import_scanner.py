"""AST-based import extraction for layer-boundary checks."""

from __future__ import annotations

import ast
from pathlib import Path


def iter_python_files(root: Path) -> list[Path]:
    return sorted(p for p in root.rglob("*.py") if p.is_file())


def imported_top_level_modules(py_file: Path) -> list[str]:
    """Return imported module strings (e.g. ``src.domain.project``, ``streamlit``)."""
    source = py_file.read_text(encoding="utf-8")
    tree = ast.parse(source, filename=str(py_file))
    out: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                out.append(alias.name)
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                out.append(node.module)
    return out


def any_module_matches(modules: list[str], *, prefixes: tuple[str, ...]) -> list[str]:
    hits: list[str] = []
    for mod in modules:
        for p in prefixes:
            if mod == p or mod.startswith(p + "."):
                hits.append(mod)
                break
    return hits
