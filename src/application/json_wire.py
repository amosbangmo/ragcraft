"""
JSON-serializable normalization for HTTP wire payloads (application layer).

Mirrors :mod:`src.infrastructure.web.json_normalization` output shape so API responses stay stable.
The application layer must not import ``src.infrastructure`` (see architecture tests).
"""

from __future__ import annotations

from typing import Any

from langchain_core.documents import Document


def jsonify_value(value: Any) -> Any:
    """Recursively normalize values for JSON (dicts, lists, LangChain ``Document``, etc.)."""
    if isinstance(value, Document):
        return {
            "page_content": value.page_content,
            "metadata": {str(k): jsonify_value(v) for k, v in dict(value.metadata or {}).items()},
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
