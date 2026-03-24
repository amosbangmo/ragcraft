from __future__ import annotations

import pytest

from services.config.settings import load_frontend_backend_settings


@pytest.fixture(autouse=True)
def clear_settings_cache():
    load_frontend_backend_settings.cache_clear()
    yield
    load_frontend_backend_settings.cache_clear()


def test_default_api_base_url(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("RAGCRAFT_API_BASE_URL", raising=False)
    s = load_frontend_backend_settings()
    assert "127.0.0.1" in s.api_base_url


def test_custom_api_base_url(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("RAGCRAFT_API_BASE_URL", "http://api.example:9000/")
    s = load_frontend_backend_settings()
    assert s.api_base_url == "http://api.example:9000"
