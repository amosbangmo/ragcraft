"""
Use cases must not treat ``dict`` as the primary application contract.

Typed DTOs / domain records cross the application layer; plain dicts belong at wire/serialization
boundaries (see :mod:`application.http.wire`, HTTP mappers).
"""

from __future__ import annotations

import ast
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
USE_CASES_ROOT = REPO_ROOT / "api" / "src" / "application" / "use_cases"


def _iter_use_case_py_files() -> list[Path]:
    return sorted(p for p in USE_CASES_ROOT.rglob("*.py") if "__pycache__" not in p.parts)


def _annotation_uses_dict_ban(node: ast.expr | None) -> bool:
    if node is None:
        return False
    if isinstance(node, ast.Name) and node.id == "dict":
        return True
    if isinstance(node, ast.Subscript):
        if isinstance(node.value, ast.Name) and node.value.id == "dict":
            return True
        return _annotation_uses_dict_ban(node.value)
    if isinstance(node, ast.BinOp) and isinstance(node.op, ast.BitOr):
        return _annotation_uses_dict_ban(node.left) or _annotation_uses_dict_ban(node.right)
    if isinstance(node, ast.Tuple):
        return any(_annotation_uses_dict_ban(elt) for elt in node.elts)
    return False


def _call_is_banned(node: ast.Call) -> bool:
    f = node.func
    if isinstance(f, ast.Name) and f.id == "jsonify_value":
        return True
    if isinstance(f, ast.Attribute) and f.attr == "to_dict":
        return True
    return False


class _UseCaseVisitor(ast.NodeVisitor):
    def __init__(self) -> None:
        self.hits: list[str] = []

    def visit_FunctionDef(self, node: ast.FunctionDef | ast.AsyncFunctionDef) -> None:
        if _annotation_uses_dict_ban(node.returns):
            self.hits.append(f"{node.name}: return annotation uses dict")
        for arg in node.args.args + node.args.kwonlyargs:
            if arg.annotation and _annotation_uses_dict_ban(arg.annotation):
                self.hits.append(f"{node.name}: parameter {arg.arg!r} annotation uses dict")
        self.generic_visit(node)

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
        self.visit_FunctionDef(node)

    def visit_Call(self, node: ast.Call) -> None:
        if _call_is_banned(node):
            self.hits.append(f"line {node.lineno}: banned call (to_dict / jsonify_value)")
        self.generic_visit(node)


def test_use_cases_avoid_dict_contracts_and_serialization_helpers() -> None:
    """Fail on dict-typed surfaces or inline serialization in use case modules."""
    bad: list[str] = []
    for path in _iter_use_case_py_files():
        text = path.read_text(encoding="utf-8")
        try:
            tree = ast.parse(text, filename=str(path))
        except SyntaxError as exc:
            bad.append(f"{path.relative_to(REPO_ROOT)}: syntax error {exc}")
            continue
        visitor = _UseCaseVisitor()
        visitor.visit(tree)
        for h in visitor.hits:
            bad.append(f"{path.relative_to(REPO_ROOT)}: {h}")
    msg = (
        "Use cases must use typed DTOs/domain records — not dict annotations, to_dict(), or "
        "jsonify_value(); serialize at the HTTP/wire boundary.\n"
    )
    assert not bad, msg + "\n".join(bad)
