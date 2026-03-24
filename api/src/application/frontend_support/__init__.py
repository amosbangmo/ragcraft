"""
Internal compatibility surface for the shared :class:`~services.backend.backend_client_protocol.BackendClient`
protocol type (re-export only).

The Streamlit UI talks to the backend **only over HTTP**; test-only composition helpers live under
``api/tests/support/`` — not here.
"""

from __future__ import annotations

__all__: list[str] = []
