"""
Streamlit ↔ backend boundary (compatibility).

Prefer :mod:`services.api_client` as the single import surface for pages and components.
"""

from __future__ import annotations

from services.api_client import get_backend_client, get_frontend_backend_settings

__all__ = [
    "get_backend_client",
    "get_frontend_backend_settings",
]
