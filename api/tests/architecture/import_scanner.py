"""AST-based import extraction for layer-boundary checks."""

from __future__ import annotations

import ast
from pathlib import Path


def iter_python_files(root: Path) -> list[Path]:
    return sorted(p for p in root.rglob("*.py") if p.is_file())


def imported_top_level_modules(py_file: Path) -> list[str]:
    """Return imported module strings (e.g. ``domain.project``, ``streamlit``)."""
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


def collect_import_violations(
    roots: list[Path],
    *,
    forbidden: tuple[str, ...],
    repo_root: Path,
) -> list[str]:
    """
    Scan top-level imports under each existing ``root``; return human-readable violation lines.

    Used by architecture tests to enforce package boundaries without depending on source formatting.
    """
    violations: list[str] = []
    for root in roots:
        if not root.is_dir():
            continue
        for path in iter_python_files(root):
            mods = imported_top_level_modules(path)
            bad = any_module_matches(mods, prefixes=forbidden)
            for m in bad:
                rel = path.relative_to(repo_root)
                violations.append(f"{rel}: imports {m}")
    return violations
