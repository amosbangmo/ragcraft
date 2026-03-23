"""
FastAPI HTTP delivery layer: no Streamlit in ``interfaces/http``, routers stay thin.
"""

from __future__ import annotations

from pathlib import Path

from architecture.import_scanner import collect_import_violations

REPO_ROOT = Path(__file__).resolve().parents[3]
HTTP_ROOT = REPO_ROOT / "api" / "src" / "interfaces" / "http"


def test_interfaces_http_package_avoids_streamlit() -> None:
    violations = collect_import_violations(
        [HTTP_ROOT],
        forbidden=("streamlit",),
        repo_root=REPO_ROOT,
    )
    assert not violations, "interfaces/http must not import Streamlit.\n" + "\n".join(violations)


def test_interfaces_http_avoids_frontend_packages_and_legacy_roots() -> None:
    """HTTP delivery must not import top-level frontend packages or monolith ``src`` / ``apps`` roots (Streamlit: sibling test)."""
    violations = collect_import_violations(
        [HTTP_ROOT],
        forbidden=(
            "pages",
            "components",
            "viewmodels",
            "state",
            "services",
            "utils",
            "src",
            "apps",
        ),
        repo_root=REPO_ROOT,
    )
    assert not violations, (
        "interfaces/http must not import frontend tree packages or legacy ``src.*`` / ``apps.*`` roots.\n"
        + "\n".join(violations)
    )
