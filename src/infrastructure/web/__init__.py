"""Web-facing adapters (JSON normalization for HTTP, etc.)."""

from src.infrastructure.web.json_normalization import jsonify_value

__all__ = ["jsonify_value"]
