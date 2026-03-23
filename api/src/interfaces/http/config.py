"""API-layer settings (env-backed). No business rules."""

from __future__ import annotations

import os
from dataclasses import dataclass
from functools import lru_cache


@dataclass(frozen=True)
class ApiSettings:
    api_title: str
    api_version: str


def _env_str(name: str, default: str) -> str:
    raw = os.environ.get(name)
    if raw is None or not str(raw).strip():
        return default
    return str(raw).strip()


@lru_cache(maxsize=1)
def load_settings() -> ApiSettings:
    return ApiSettings(
        api_title=_env_str("RAGCRAFT_API_TITLE", "RAGCraft API"),
        api_version=_env_str("RAGCRAFT_API_VERSION", "0.1.0"),
    )


def get_settings() -> ApiSettings:
    """FastAPI-compatible provider (no heavy imports)."""
    return load_settings()
