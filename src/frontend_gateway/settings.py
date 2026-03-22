"""Configuration for Streamlit → backend wiring (in-process vs HTTP)."""

from __future__ import annotations

import os
from dataclasses import dataclass
from functools import lru_cache


def _env_str(name: str, default: str) -> str:
    raw = os.environ.get(name)
    if raw is None or not str(raw).strip():
        return default
    return str(raw).strip()


def _env_float(name: str, default: float) -> float:
    raw = os.environ.get(name)
    if raw is None or not str(raw).strip():
        return default
    try:
        return float(raw)
    except ValueError:
        return default


@dataclass(frozen=True)
class FrontendBackendSettings:
    """
    ``RAGCRAFT_BACKEND_CLIENT`` — ``in_process`` (default) or ``http``.

    ``RAGCRAFT_API_BASE_URL`` — root URL for the FastAPI app (no trailing slash), e.g.
    ``http://127.0.0.1:8000``.
    """

    backend_client_mode: str
    api_base_url: str
    timeout_seconds: float


@lru_cache(maxsize=1)
def load_frontend_backend_settings() -> FrontendBackendSettings:
    mode = _env_str("RAGCRAFT_BACKEND_CLIENT", "in_process").lower()
    return FrontendBackendSettings(
        backend_client_mode=mode,
        api_base_url=_env_str("RAGCRAFT_API_BASE_URL", "http://127.0.0.1:8000").rstrip("/"),
        timeout_seconds=_env_float("RAGCRAFT_API_TIMEOUT_SECONDS", 300.0),
    )


def use_http_backend_client() -> bool:
    return load_frontend_backend_settings().backend_client_mode in ("http", "api", "remote")
