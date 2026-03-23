"""
JSON-serializable normalization for HTTP wire payloads (application layer).

Mirrors :mod:`infrastructure.rag.web.json_normalization` output shape so API responses stay stable.
The application layer must not import concrete ``infrastructure`` adapters (see architecture tests).
"""

from __future__ import annotations

from typing import Any


def _is_document_like(value: Any) -> bool:
    return (
        hasattr(value, "page_content")
        and hasattr(value, "metadata")
        and not isinstance(value, type)
    )


def jsonify_value(value: Any) -> Any:
    """Recursively normalize values for JSON (dicts, lists, document-like objects with page_content/metadata, etc.)."""
    if _is_document_like(value):
        return {
            "page_content": getattr(value, "page_content", "") or "",
            "metadata": {
                str(k): jsonify_value(v)
                for k, v in dict(getattr(value, "metadata", None) or {}).items()
            },
        }
    if isinstance(value, dict):
        return {str(k): jsonify_value(v) for k, v in value.items()}
    if isinstance(value, list):
        return [jsonify_value(x) for x in value]
    if isinstance(value, tuple):
        return [jsonify_value(x) for x in value]
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value
    if hasattr(value, "value") and not isinstance(value, type):
        inner = getattr(value, "value")
        if isinstance(inner, (str, int, float, bool)):
            return inner
    if hasattr(value, "to_dict") and callable(value.to_dict):
        return jsonify_value(value.to_dict())
    return str(value)
