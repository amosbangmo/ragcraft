"""Translate FastAPI / RAGCraft error JSON into domain exceptions or :class:`BackendHttpError`."""

from __future__ import annotations

from typing import Any

from src.core.exceptions import (
    DocStoreError,
    LLMServiceError,
    RAGCraftError,
    VectorStoreError,
)
from src.frontend_gateway.errors import BackendHttpError

_TYPE_MAP: dict[str, type[RAGCraftError]] = {
    "LLMServiceError": LLMServiceError,
    "VectorStoreError": VectorStoreError,
    "DocStoreError": DocStoreError,
}


def raise_for_api_response(
    status_code: int,
    payload: dict[str, Any] | None,
    fallback_text: str,
) -> None:
    """Always raises (never returns)."""
    message = _extract_message(payload, fallback_text)
    if payload:
        et = str(payload.get("error_type") or "")
        cls = _TYPE_MAP.get(et)
        if cls is not None:
            raise cls(message, user_message=message)
    raise BackendHttpError(message, status_code=status_code, payload=payload)


def _extract_message(payload: dict[str, Any] | None, fallback: str) -> str:
    if not payload:
        return fallback or "Request failed."
    for key in ("message", "detail"):
        v = payload.get(key)
        if isinstance(v, str) and v.strip():
            return v.strip()
    return fallback or "Request failed."
