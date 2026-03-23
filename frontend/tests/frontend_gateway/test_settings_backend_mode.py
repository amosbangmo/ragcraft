from __future__ import annotations

import pytest

from services.settings import load_frontend_backend_settings, use_http_backend_client


@pytest.fixture(autouse=True)
def clear_settings_cache():
    load_frontend_backend_settings.cache_clear()
    yield
    load_frontend_backend_settings.cache_clear()


def test_use_http_backend_client_true_by_default(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("RAGCRAFT_BACKEND_CLIENT", raising=False)
    assert use_http_backend_client() is True


def test_use_http_backend_client_false_when_in_process(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("RAGCRAFT_BACKEND_CLIENT", "in_process")
    assert use_http_backend_client() is False


@pytest.mark.parametrize(
    "mode",
    ("http", "HTTP", "api", "remote"),
)
def test_use_http_backend_client_true_for_remote_modes(
    monkeypatch: pytest.MonkeyPatch, mode: str
) -> None:
    monkeypatch.setenv("RAGCRAFT_BACKEND_CLIENT", mode)
    assert use_http_backend_client() is True
