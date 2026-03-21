"""Canonical JSON shape for HTTP API errors (transport + mapped domain errors)."""

from __future__ import annotations

from typing import Any


def api_error_body(
    *,
    message: str,
    error_type: str,
    code: str,
    category: str,
    extra: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """
    Build a consistent error object for JSON responses.

    - ``detail`` / ``message``: human-readable text for the client (no stack traces).
    - ``error_type``: concrete exception class name when applicable.
    - ``code``: stable machine identifier.
    - ``category``: ``domain`` | ``application`` | ``infrastructure`` | ``transport`` | ``internal``.
    """
    body: dict[str, Any] = {
        "detail": message,
        "message": message,
        "error_type": error_type,
        "code": code,
        "category": category,
    }
    if extra:
        body.update(extra)
    return body
