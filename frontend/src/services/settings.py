"""HTTP client settings for Streamlit → FastAPI (base URL and timeouts)."""

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


def _env_float_optional(name: str) -> float | None:
    raw = os.environ.get(name)
    if raw is None or not str(raw).strip():
        return None
    try:
        return float(raw)
    except ValueError:
        return None


@dataclass(frozen=True)
class FrontendBackendSettings:
    """
    ``RAGCRAFT_API_BASE_URL`` — root URL for the FastAPI app (no trailing slash), e.g.
    ``http://127.0.0.1:8000``.

    ``RAGCRAFT_API_CONNECT_TIMEOUT_SECONDS`` — TCP/TLS handshake timeout (default ``10``).

    ``RAGCRAFT_API_READ_TIMEOUT_SECONDS`` — per-request read timeout for long RAG calls
    (default: ``RAGCRAFT_API_TIMEOUT_SECONDS`` or ``300``).

    ``RAGCRAFT_API_TIMEOUT_SECONDS`` — legacy default used when read timeout is not set explicitly.
    """

    api_base_url: str
    api_connect_timeout_seconds: float
    api_read_timeout_seconds: float

    @property
    def timeout_seconds(self) -> float:
        return self.api_read_timeout_seconds


@lru_cache(maxsize=1)
def load_frontend_backend_settings() -> FrontendBackendSettings:
    legacy_read = _env_float("RAGCRAFT_API_TIMEOUT_SECONDS", 300.0)
    read_override = _env_float_optional("RAGCRAFT_API_READ_TIMEOUT_SECONDS")
    return FrontendBackendSettings(
        api_base_url=_env_str("RAGCRAFT_API_BASE_URL", "http://127.0.0.1:8000").rstrip("/"),
        api_connect_timeout_seconds=_env_float("RAGCRAFT_API_CONNECT_TIMEOUT_SECONDS", 10.0),
        api_read_timeout_seconds=read_override if read_override is not None else legacy_read,
    )
