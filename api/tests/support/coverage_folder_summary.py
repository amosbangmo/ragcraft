"""
Per top-level folder coverage under ``api/tests`` when using pytest-cov dynamic contexts.

Requires ``pytest ... --cov=api/src --cov-context=test`` so each line is tagged with the
running test id (``tests/<folder>/...``).

Hit lines are merged in chunks to avoid SQLite parameter limits and aggregate-function edge
cases when hundreds of test contexts belong to one folder.
"""

from __future__ import annotations

from collections import defaultdict
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[3]
_API_TESTS = _REPO_ROOT / "api" / "tests"
_SRC = _REPO_ROOT / "api" / "src"


def _folder_from_context(ctx: str) -> str | None:
    if not ctx or "|" not in ctx:
        return None
    path_part = ctx.split("|", 1)[0].split("::", 1)[0]
    parts = Path(path_part).as_posix().split("/")
    if len(parts) >= 2 and parts[0] == "tests":
        return parts[1]
    return None


def _top_level_test_dirs() -> list[str]:
    if not _API_TESTS.is_dir():
        return []
    out: list[str] = []
    for p in sorted(_API_TESTS.iterdir()):
        if not p.is_dir() or p.name.startswith("_") or p.name == "__pycache__":
            continue
        out.append(p.name)
    return out


def _is_measured_api_src_tree(path: str) -> bool:
    """True for files under ``api/src`` (any path style pytest-cov may record)."""
    posix = Path(path).as_posix().replace("\\", "/")
    if posix.startswith("api/src/") or posix == "api/src":
        return True
    for root in ("application/", "domain/", "infrastructure/", "composition/", "interfaces/"):
        if posix.startswith(root):
            return True
    try:
        rp = Path(path).resolve()
        base = _SRC.resolve()
        return base in rp.parents or rp == base
    except OSError:
        return False


def _file_key(fname: str) -> str:
    return Path(fname).as_posix().replace("\\", "/")


def _merge_hits_for_context_range(
    data,
    contexts: list[str],
    hits: dict[str, set[int]],
    start: int,
    end: int,
) -> None:
    """Merge line hits for ``contexts[start:end]``, splitting on SQLite errors (divide & conquer)."""
    from coverage.exceptions import DataError

    if start >= end:
        return
    chunk = contexts[start:end]
    try:
        data.set_query_contexts(chunk)
        for fname in data.measured_files():
            lines = data.lines(fname)
            if lines:
                hits[_file_key(fname)].update(lines)
    except DataError:
        if end - start <= 1:
            return
        mid = (start + end) // 2
        _merge_hits_for_context_range(data, contexts, hits, start, mid)
        _merge_hits_for_context_range(data, contexts, hits, mid, end)


def _union_hit_lines(data, contexts: list[str]) -> dict[str, set[int]]:
    hits: dict[str, set[int]] = defaultdict(set)
    if not contexts:
        return hits
    _merge_hits_for_context_range(data, contexts, hits, 0, len(contexts))
    data.set_query_contexts(None)
    return hits


def _folder_coverage_percent(cov, contexts: list[str]) -> float:
    data = cov.get_data()
    hit_by_file = _union_hit_lines(data, contexts)

    total_exec = 0
    total_hit = 0
    for fname in data.measured_files():
        if not _is_measured_api_src_tree(fname):
            continue
        try:
            _, statements, _, _, _ = cov.analysis2(fname)
        except OSError:
            continue
        exec_s = set(statements)
        if not exec_s:
            continue
        h = hit_by_file.get(_file_key(fname), set())
        total_exec += len(exec_s)
        total_hit += len(exec_s & h)

    if total_exec == 0:
        return 0.0
    return 100.0 * total_hit / total_exec


def maybe_print_api_tests_folder_coverage(terminalreporter, config) -> None:
    if getattr(config.option, "no_cov", False):
        return
    cov_source = getattr(config.option, "cov_source", None) or []
    if not cov_source:
        return
    if getattr(config.option, "cov_context", None) != "test":
        terminalreporter.write_line("")
        terminalreporter.write_line(
            "Coverage by api/tests/* folder: pass --cov-context=test with --cov to enable."
        )
        return

    try:
        import coverage
        from coverage.exceptions import CoverageException
    except ImportError:
        return

    cov = coverage.Coverage(source=[str(_SRC.resolve())])
    try:
        cov.load()
    except CoverageException:
        return

    data = cov.get_data()
    contexts = list(data.measured_contexts())
    by_folder: dict[str, list[str]] = defaultdict(list)
    for ctx in contexts:
        folder = _folder_from_context(ctx)
        if folder:
            by_folder[folder].append(ctx)

    if not by_folder:
        return

    terminalreporter.write_line("")
    terminalreporter.write_line(
        "Coverage % of api/src (executable lines touched while running tests in that folder):"
    )
    terminalreporter.write_line("-" * 72)

    for name in _top_level_test_dirs():
        ctxs = by_folder.get(name)
        if not ctxs:
            terminalreporter.write_line(f"  {name:22}  (no tests executed)")
            continue
        pct = _folder_coverage_percent(cov, ctxs)
        terminalreporter.write_line(f"  {name:22}  {pct:5.1f}%")

    terminalreporter.write_line("-" * 72)
