#!/usr/bin/env python3
"""
Écrit ``repo_bundle.txt`` à la racine du dépôt :
- tous les ``*.py`` du dépôt (hors ``.git``, ``node_modules``, venv, ``__pycache__``, etc.) ;
- puis tout fichier sous ``docs/``, ``cypress/``, ``artifacts/`` (sans dupliquer un chemin déjà écrit).

Fichiers binaires : marqueur + taille, pas d’octets bruts.
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "repo_bundle.txt"

SKIP_DIR_NAMES = frozenset(
    {
        ".git",
        "node_modules",
        ".venv",
        "venv",
        "__pycache__",
        ".pytest_cache",
        ".mypy_cache",
        "dist",
        "build",
        ".tox",
        ".eggs",
    }
)


def path_should_skip(rel: Path) -> bool:
    for part in rel.parts:
        if part in SKIP_DIR_NAMES:
            return True
        if part == "__pycache__":
            return True
        if part.endswith(".egg-info"):
            return True
    return False


def collect_py_files() -> list[Path]:
    found: list[Path] = []
    for p in ROOT.rglob("*.py"):
        try:
            rel = p.relative_to(ROOT)
        except ValueError:
            continue
        if path_should_skip(rel):
            continue
        found.append(p)
    found.sort(key=lambda x: x.as_posix().lower())
    return found


def collect_under(sub: str) -> list[Path]:
    base = ROOT / sub
    if not base.is_dir():
        return []
    found: list[Path] = []
    for p in base.rglob("*"):
        if p.is_dir():
            continue
        try:
            rel = p.relative_to(ROOT)
        except ValueError:
            continue
        if path_should_skip(rel):
            continue
        found.append(p)
    found.sort(key=lambda x: x.as_posix().lower())
    return found


def looks_binary(data: bytes) -> bool:
    if not data:
        return False
    if b"\x00" in data[:4096]:
        return True
    sample = data[:8000]
    n = len(sample)
    if n == 0:
        return False
    non_text = sum(1 for b in sample if b < 9 or (b > 13 and b < 32 and b not in (9, 10, 13)))
    return non_text / n > 0.02


def write_blob(fout, rel_posix: str, path: Path) -> None:
    fout.write(f"===================={rel_posix}====================\n")
    try:
        data = path.read_bytes()
    except OSError as exc:
        fout.write(f"[Lecture impossible: {exc}]\n\n")
        return
    if looks_binary(data):
        fout.write(f"[Fichier binaire, {len(data)} octets — contenu non inclus en texte]\n\n")
        return
    try:
        text = data.decode("utf-8")
    except UnicodeDecodeError:
        text = data.decode("utf-8", errors="replace")
    fout.write(text)
    if text and not text.endswith("\n"):
        fout.write("\n")
    fout.write("\n")


def main() -> int:
    emitted: set[str] = set()
    out_lines = 0

    with OUT.open("w", encoding="utf-8", newline="\n") as fout:
        for p in collect_py_files():
            rel = p.relative_to(ROOT).as_posix()
            if rel in emitted:
                continue
            write_blob(fout, rel, p)
            emitted.add(rel)
            out_lines += 1

        for sub in ("docs", "cypress", "artifacts"):
            for p in collect_under(sub):
                rel = p.relative_to(ROOT).as_posix()
                if rel in emitted:
                    continue
                write_blob(fout, rel, p)
                emitted.add(rel)
                out_lines += 1

    if out_lines == 0:
        print("Aucun fichier à inclure.", file=sys.stderr)
        return 1

    print(f"Écrit {OUT} ({out_lines} fichiers uniques).", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
