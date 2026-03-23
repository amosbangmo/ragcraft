"""
FastAPI dependency wiring must not import Streamlit for the chain-cache eviction path.

The full service graph may still load UI-oriented modules elsewhere; this file guards the
``interfaces.http.dependencies`` import surface and the cache-invalidate route contract.
"""

from __future__ import annotations

import pathlib
import sys

from fastapi.testclient import TestClient

from interfaces.http.dependencies import get_invalidate_project_chain_cache_use_case
from interfaces.http.main import create_app
from api.bearer_auth import bearer_headers


def test_import_dependencies_module_does_not_load_streamlit() -> None:
    for name in list(sys.modules):
        if name == "streamlit" or name.startswith("streamlit."):
            del sys.modules[name]

    import interfaces.http.dependencies  # noqa: F401

    assert "streamlit" not in sys.modules


def test_dependencies_module_statically_avoids_streamlit_token() -> None:
    root = pathlib.Path(__file__).resolve().parents[3]
    text = (root / "api" / "src" / "interfaces" / "http" / "dependencies.py").read_text(
        encoding="utf-8"
    )
    assert "streamlit" not in text.lower()


def test_post_invalidate_retrieval_cache_invokes_use_case() -> None:
    calls: list[tuple[str, str]] = []

    class _FakeInvalidateProjectChain:
        def execute(self, *, user_id: str, project_id: str) -> None:
            calls.append((user_id, project_id))

    app = create_app()
    app.dependency_overrides[get_invalidate_project_chain_cache_use_case] = (
        lambda: _FakeInvalidateProjectChain()
    )
    try:
        with TestClient(app) as client:
            r = client.post(
                "/projects/demo/retrieval-cache/invalidate",
                headers=bearer_headers(user_id="alice"),
            )
    finally:
        app.dependency_overrides.clear()

    assert r.status_code == 200
    assert r.json() == {"ok": True}
    assert calls == [("alice", "demo")]
