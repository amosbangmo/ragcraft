"""
Text-level guardrails: pre-migration path strings must not appear in sources or docs.

Tokens are built from fragments so this module's own source does not trip the scan.
Complements :mod:`architecture.test_repository_structure` (physical roots) and import scans.
"""

from __future__ import annotations

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
_THIS = Path(__file__).resolve()

# (prefix, suffix) → forbidden legacy substring (audit: apps/api, src.ui, src/ui, frontend_gateway)
_LEGACY_TOKEN_PARTS: tuple[tuple[str, str], ...] = (
    ("apps", "/api"),
    ("apps", "\\api"),
    ("src", ".ui"),
    ("src", "/ui"),
    ("frontend_", "gateway"),
)

_LEGACY_TOKENS: tuple[str, ...] = tuple(a + b for a, b in _LEGACY_TOKEN_PARTS)

_SKIP_DIR_NAMES = frozenset(
    {
        ".git",
        ".venv",
        ".mypy_cache",
        ".pytest_cache",
        ".ruff_cache",
        "__pycache__",
        "node_modules",
        "dist",
        "build",
        ".eggs",
    }
)

# Only these trees (plus a few root-level text files) are scanned — avoids walking .venv / tooling caches.
_SCAN_ROOT_DIRS = ("api", "frontend", "docs", "scripts", ".github")

_TEXT_SUFFIXES = frozenset(
    {
        ".py",
        ".md",
        ".txt",
        ".yml",
        ".yaml",
        ".json",
        ".toml",
        ".ini",
        ".cfg",
        ".sh",
        ".bat",
        ".ps1",
    }
)


def _iter_scan_files() -> list[Path]:
    out: list[Path] = []
    for name in _SCAN_ROOT_DIRS:
        root = REPO_ROOT / name
        if not root.is_dir():
            continue
        for path in root.rglob("*"):
            if not path.is_file():
                continue
            if path.resolve() == _THIS:
                continue
            if any(part in _SKIP_DIR_NAMES or part.startswith(".") for part in path.parts):
                continue
            if path.suffix.lower() not in _TEXT_SUFFIXES:
                continue
            out.append(path)
    for path in REPO_ROOT.iterdir():
        if not path.is_file() or path.resolve() == _THIS:
            continue
        if path.suffix.lower() not in _TEXT_SUFFIXES:
            continue
        out.append(path)
    return sorted(out)


def _read_text(path: Path) -> str | None:
    try:
        return path.read_text(encoding="utf-8")
    except OSError:
        return None
    except UnicodeDecodeError:
        return None


def test_no_legacy_path_tokens_in_text_sources() -> None:
    """Fail if docs or code still mention removed monolith / alternate layout paths."""
    hits: list[str] = []
    for path in _iter_scan_files():
        text = _read_text(path)
        if text is None:
            continue
        lower = text.lower()
        for token in _LEGACY_TOKENS:
            if token.lower() in lower:
                rel = path.relative_to(REPO_ROOT).as_posix()
                hits.append(f"{rel}: contains legacy token {token!r}")
    msg = (
        "Remove legacy layout references (apps/api, src.ui, src/ui, frontend_gateway) from sources and docs.\n"
    )
    assert not hits, msg + "\n".join(hits)


def test_no_frontend_gateway_directory_segment() -> None:
    """Directory name ``frontend_gateway`` must not exist under scanned project trees."""
    bad: list[str] = []
    for name in _SCAN_ROOT_DIRS:
        root = REPO_ROOT / name
        if not root.is_dir():
            continue
        for path in root.rglob("*"):
            if any(part in _SKIP_DIR_NAMES or part.startswith(".") for part in path.parts):
                continue
            for part in path.parts:
                if part == "frontend_gateway":
                    bad.append(path.relative_to(REPO_ROOT).as_posix())
                    break
    assert not bad, "Remove frontend_gateway path segments:\n  " + "\n  ".join(sorted(set(bad)))
