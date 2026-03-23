#!/usr/bin/env python3
"""
Write a single text bundle at repo root: all *.py files, plus docs/ and artifacts/.

Usage: python scripts/build_source_bundle.py [--output PATH]
Default output: repo_source_bundle.txt (repo root).
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUT = ROOT / "repo_source_bundle.txt"

IGNORE_DIR_NAMES = frozenset(
    {
        ".git",
        "__pycache__",
        ".venv",
        "venv",
        ".eggs",
        "node_modules",
        ".pytest_cache",
        ".mypy_cache",
        ".ruff_cache",
        ".tox",
        "dist",
        "build",
        "htmlcov",
    }
)


def path_under_ignored_dir(rel: Path) -> bool:
    return bool(rel.parts) and any(p in IGNORE_DIR_NAMES for p in rel.parts)


def iter_py_files() -> list[Path]:
    out: list[Path] = []
    for p in ROOT.rglob("*.py"):
        if not p.is_file():
            continue
        rel = p.relative_to(ROOT)
        if path_under_ignored_dir(rel):
            continue
        out.append(p)
    return sorted(out, key=lambda x: str(x).lower())


def iter_tree_files(sub: str) -> list[Path]:
    base = ROOT / sub
    if not base.is_dir():
        return []
    files: list[Path] = []
    for p in base.rglob("*"):
        if p.is_file():
            rel = p.relative_to(ROOT)
            if path_under_ignored_dir(rel):
                continue
            files.append(p)
    return sorted(files, key=lambda x: str(x).lower())


def rel_posix(path: Path) -> str:
    return path.relative_to(ROOT).as_posix()


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="replace")


def write_bundle(out_path: Path) -> None:
    sections: list[str] = []

    for py in iter_py_files():
        rel = rel_posix(py)
        sections.append(f"===================={rel}====================\n")
        sections.append(read_text(py))
        if not sections[-1].endswith("\n"):
            sections.append("\n")
        sections.append("\n")

    for doc in iter_tree_files("docs"):
        rel = rel_posix(doc)
        sections.append(f"===================={rel}====================\n")
        sections.append(read_text(doc))
        if not sections[-1].endswith("\n"):
            sections.append("\n")
        sections.append("\n")

    for art in iter_tree_files("artifacts"):
        rel = rel_posix(art)
        sections.append(f"===================={rel}====================\n")
        sections.append(read_text(art))
        if not sections[-1].endswith("\n"):
            sections.append("\n")
        sections.append("\n")

    out_path.write_text("".join(sections), encoding="utf-8")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument(
        "--output",
        "-o",
        type=Path,
        default=DEFAULT_OUT,
        help=f"Output file (default: {DEFAULT_OUT.name} at repo root)",
    )
    args = ap.parse_args()
    out = args.output
    if not out.is_absolute():
        out = ROOT / out
    write_bundle(out)
    print(f"Wrote {out} ({out.stat().st_size} bytes)", file=sys.stderr)


if __name__ == "__main__":
    main()
