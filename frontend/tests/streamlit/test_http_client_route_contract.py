"""
Contract: HTTP client paths stay aligned with FastAPI routes (catch renames / typos early).

Uses file text instead of importing ``http_client`` so optional runtime deps do not block collection.
"""

from __future__ import annotations

from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[3]
_HTTP_CLIENT = (
    _REPO_ROOT / "frontend" / "src" / "services" / "http_backend_client.py"
)
_SERVICES = _REPO_ROOT / "frontend" / "src" / "services"
_STREAMLIT_AUTH = _SERVICES / "streamlit_auth.py"


def test_http_client_defines_core_rag_and_project_paths() -> None:
    text = _HTTP_CLIENT.read_text(encoding="utf-8")
    required = [
        '"/chat/ask"',
        '"/chat/pipeline/inspect"',
        '"/chat/pipeline/preview-summary-recall"',
        '"/chat/retrieval/compare"',
        '"/projects"',
    ]
    missing = [p for p in required if p not in text]
    assert not missing, f"missing path literals in http_client: {missing}"


def test_streamlit_auth_targets_login_and_register_routes() -> None:
    text = _STREAMLIT_AUTH.read_text(encoding="utf-8")
    assert '"/auth/login"' in text
    assert '"/auth/register"' in text
