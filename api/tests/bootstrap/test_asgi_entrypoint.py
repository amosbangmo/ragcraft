"""Uvicorn entrypoint and FastAPI factory smoke tests (stale import / layout regressions)."""

from __future__ import annotations

import importlib.util
from pathlib import Path

from fastapi import FastAPI
from fastapi.testclient import TestClient


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[3]


def test_api_main_py_wires_interfaces_create_app() -> None:
    """``api/main.py`` must keep the ASGI bootstrap path used by ``uvicorn api.main:app``."""
    main_py = _repo_root() / "api" / "main.py"
    text = main_py.read_text(encoding="utf-8")
    assert "interfaces.http.main" in text
    assert "create_app" in text


def test_create_app_exposes_health_and_openapi() -> None:
    from interfaces.http.main import create_app

    app = create_app()
    assert isinstance(app, FastAPI)
    with TestClient(app) as client:
        assert client.get("/health").status_code == 200
        assert client.get("/openapi.json").status_code == 200
        spec = client.get("/openapi.json").json()
        assert "paths" in spec and "/health" in spec["paths"]


def test_uvicorn_api_main_module_exposes_app_instance() -> None:
    """
    Load ``api/main.py`` like uvicorn without importing the top-level ``api`` package name.

    ``PYTHONPATH`` often includes ``api/tests``, where a separate ``api`` test package exists;
    ``importlib.util.spec_from_file_location`` avoids that collision.
    """
    main_py = _repo_root() / "api" / "main.py"
    spec = importlib.util.spec_from_file_location(
        "_bootstrap_loaded_api_main",
        main_py,
    )
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    assert isinstance(mod.app, FastAPI)
    with TestClient(mod.app) as client:
        assert client.get("/health").json() == {"status": "ok"}
