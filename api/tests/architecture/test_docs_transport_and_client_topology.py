"""
Public docs must not reintroduce alternate Streamlit/backend transports or contradictory client topology.

The product UI uses HTTP only; composition helpers live under ``api/tests/support/``.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[3]
_DOCS = REPO_ROOT / "docs"
_ROOT_README = REPO_ROOT / "README.md"
_ARCH_TARGET = REPO_ROOT / "ARCHITECTURE_TARGET.md"


def _markdown_files() -> list[Path]:
    out = sorted(_DOCS.glob("*.md"))
    if _ROOT_README.is_file():
        out.append(_ROOT_README)
    if _ARCH_TARGET.is_file():
        out.append(_ARCH_TARGET)
    return out


def _line_allows_removed_in_process_transport(line: str) -> bool:
    """Allow historical mentions that explicitly say the mode was removed or is forbidden."""
    lower = line.lower()
    if "removed" in lower or "no longer" in lower or "not supported" in lower:
        return True
    if "forbid" in lower or ("must not" in lower and "in_process" in line):
        return True
    return False


@pytest.mark.architecture
@pytest.mark.parametrize("path", _markdown_files(), ids=lambda p: p.relative_to(REPO_ROOT).as_posix())
def test_docs_do_not_document_ui_in_process_backend_client(path: Path) -> None:
    text = path.read_text(encoding="utf-8")
    bad: list[str] = []
    for i, line in enumerate(text.splitlines(), start=1):
        if _line_allows_removed_in_process_transport(line):
            continue
        if "RAGCRAFT_BACKEND_CLIENT=in_process" in line or "RAGCRAFT_BACKEND_CLIENT = in_process" in line:
            bad.append(f"{path.name}:{i}: documents in_process backend client env")
        if re.search(r"\bapi\b.*\bremote\b.*\bin_process\b", line) and "RAGCRAFT_BACKEND_CLIENT" in line:
            bad.append(f"{path.name}:{i}: lists multiple RAGCRAFT_BACKEND_CLIENT transport modes")
        if "in-process" in line.lower() and "streamlit" in line.lower() and "http" not in line.lower():
            if "test" in line.lower() or "composition" in line.lower():
                continue
            # Narrative that Streamlit uses in-process (not HTTP).
            if any(
                x in line.lower()
                for x in (
                    "uses in-process",
                    "in-process mode",
                    "in-process client",
                    "in-process backend",
                    "in-process wiring",
                )
            ):
                bad.append(f"{path.name}:{i}: implies Streamlit in-process transport")
    assert not bad, "Doc drift — UI must be HTTP-only:\n" + "\n".join(bad)


@pytest.mark.architecture
def test_docs_do_not_claim_streamlit_backend_factory_module_exists() -> None:
    """The old ``streamlit_backend_factory`` module was removed; composition lives in ``api/tests/support/``."""
    hits: list[str] = []
    for path in _markdown_files():
        if path.name == "migration_report_final.md":
            continue
        text = path.read_text(encoding="utf-8")
        if "streamlit_backend_factory" in text:
            hits.append(f"{path.name}: still mentions streamlit_backend_factory (removed module)")
    assert not hits, "\n".join(hits)
