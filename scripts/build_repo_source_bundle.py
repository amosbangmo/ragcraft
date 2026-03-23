#!/usr/bin/env python3
"""
Assemble a single text bundle at repo root: all .py files, plus docs/, cypress/, artifacts/.
"""
from __future__ import annotations

import base64
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "SOURCE_BUNDLE.txt"

SKIP_DIR_NAMES = frozenset(
    {
        ".git",
        "node_modules",
        "__pycache__",
        ".venv",
        "venv",
        ".pytest_cache",
        ".mypy_cache",
        ".tox",
        "dist",
        "build",
        ".eggs",
    }
)


def to_posix(relative: Path) -> str:
    return relative.as_posix()


def iter_py_files() -> list[Path]:
    found: list[Path] = []
    root_s = str(ROOT)
    for dirpath, dirnames, filenames in os.walk(root_s, topdown=True):
        dirnames[:] = [
            d
            for d in dirnames
            if d not in SKIP_DIR_NAMES and not d.endswith(".egg-info")
        ]
        for name in filenames:
            if name.endswith(".py"):
                found.append(Path(dirpath) / name)
    found.sort(key=lambda p: p.relative_to(ROOT).as_posix())
    return found


def iter_tree(root_sub: str) -> list[Path]:
    base = ROOT / root_sub
    if not base.is_dir():
        return []
    paths = sorted(base.rglob("*"), key=lambda p: p.relative_to(ROOT).as_posix())
    return [p for p in paths if p.is_file()]


def is_probably_text(data: bytes) -> bool:
    if not data:
        return True
    if b"\x00" in data[:4096]:
        return False
    try:
        data.decode("utf-8")
        return True
    except UnicodeDecodeError:
        return False


def file_block(rel: str, data: bytes) -> str:
    header = f"===================={rel}====================\n"
    if is_probably_text(data):
        text = data.decode("utf-8")
        if text and not text.endswith("\n"):
            text += "\n"
        return header + text
    b64 = base64.standard_b64encode(data).decode("ascii")
    return header + "[BINARY_BASE64]\n" + b64 + "\n"


def main() -> None:
    parts: list[str] = []

    for path in iter_py_files():
        rel = to_posix(path.relative_to(ROOT))
        data = path.read_bytes()
        parts.append(file_block(rel, data))
        parts.append("\n")

    for path in iter_tree("docs"):
        rel = to_posix(path.relative_to(ROOT))
        parts.append(file_block(rel, path.read_bytes()))
        parts.append("\n")

    for path in iter_tree("cypress"):
        rel = to_posix(path.relative_to(ROOT))
        parts.append(file_block(rel, path.read_bytes()))
        parts.append("\n")

    for path in iter_tree("artifacts"):
        rel = to_posix(path.relative_to(ROOT))
        parts.append(file_block(rel, path.read_bytes()))
        parts.append("\n")

    OUT.write_text("".join(parts), encoding="utf-8", newline="\n")
    print(f"Wrote {OUT} ({OUT.stat().st_size} bytes)")


if __name__ == "__main__":
    main()
