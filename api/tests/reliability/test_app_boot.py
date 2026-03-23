"""Application boots: ASGI factory and public endpoints respond."""

from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from interfaces.http.main import create_app


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[3]


@pytest.mark.reliability
def test_create_app_returns_fastapi_instance() -> None:
    app = create_app()
    assert isinstance(app, FastAPI)


@pytest.mark.reliability
def test_health_version_openapi_public_routes() -> None:
    app = create_app()
    with TestClient(app) as client:
        h = client.get("/health")
        assert h.status_code == 200
        assert h.json().get("status") == "ok"

        v = client.get("/version")
        assert v.status_code == 200
        body = v.json()
        assert body.get("service") or body.get("name")
        assert "version" in body

        spec = client.get("/openapi.json")
        assert spec.status_code == 200
        data = spec.json()
        assert "/health" in data.get("paths", {})


@pytest.mark.reliability
def test_api_main_py_exposes_app_for_uvicorn() -> None:
    """Same entry style as ``uvicorn api.main:app`` (file load avoids test-package name clash)."""
    main_py = _repo_root() / "api" / "main.py"
    spec = importlib.util.spec_from_file_location(
        "_reliability_loaded_api_main",
        main_py,
    )
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    assert isinstance(mod.app, FastAPI)
    with TestClient(mod.app) as client:
        assert client.get("/health").status_code == 200
