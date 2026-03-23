"""Composition must not depend on transport/UI packages (ports + infrastructure adapters only)."""

from __future__ import annotations

from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[3]
COMPOSITION_PY = sorted((REPO_ROOT / "api" / "src" / "composition").glob("*.py"))


def _forbidden_transport_import_line(line: str) -> bool:
    s = line.strip()
    if s.startswith("#") or not s:
        return False
    if s.startswith("from services"):
        return True
    if s.startswith("import services") and (
        s == "import services" or s.startswith("import services.")
    ):
        return True
    return False


@pytest.mark.parametrize(
    "path",
    COMPOSITION_PY,
    ids=[p.name for p in COMPOSITION_PY],
)
def test_composition_modules_do_not_import_services_package(path: Path) -> None:
    text = path.read_text(encoding="utf-8").replace("\r\n", "\n")
    hits = [ln for ln in text.splitlines() if _forbidden_transport_import_line(ln)]
    assert not hits, (
        f"{path.relative_to(REPO_ROOT)} must not import services "
        f"(use ports + infrastructure adapters; Streamlit transcript is wired in "
        f"application.frontend_support.streamlit_backend_factory):\n"
        + "\n".join(hits)
    )
