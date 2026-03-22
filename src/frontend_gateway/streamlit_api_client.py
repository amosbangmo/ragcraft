"""
Streamlit ↔ backend boundary: one entrypoint for :class:`~src.frontend_gateway.protocol.BackendClient`.

Pages and ``src/ui`` should depend on :func:`get_backend_client` from this module (or
:mod:`src.frontend_gateway.streamlit_context`, which re-exports it). **Do not** import
:class:`~src.app.ragcraft_app.RAGCraftApp` from pages — the façade is an implementation detail
of in-process mode only.

Modes (environment)
-------------------

``RAGCRAFT_BACKEND_CLIENT``
    * ``in_process`` (default) — same Python process as Streamlit; uses
      :class:`~src.frontend_gateway.in_process.InProcessBackendClient`.
    * ``http``, ``api``, or ``remote`` — calls the FastAPI app via
      :class:`~src.frontend_gateway.http_client.HttpBackendClient`.

``RAGCRAFT_API_BASE_URL``
    Root URL without trailing slash, e.g. ``http://127.0.0.1:8000``.

``RAGCRAFT_API_CONNECT_TIMEOUT_SECONDS`` (default ``10``)
    Connection timeout.

``RAGCRAFT_API_READ_TIMEOUT_SECONDS``
    Read timeout for long requests. If unset, ``RAGCRAFT_API_TIMEOUT_SECONDS`` is used (default ``300``).

Vertical slices already wired through ``BackendClient`` (projects list/create, chat ask, pipeline
inspect, gold QA dataset run, exports, etc.) automatically use FastAPI when HTTP mode is enabled —
no per-page branching required.

.. todo::

    Remaining screens that still touch ``AuthService`` or SQLite directly for auth should move
    behind ``BackendClient`` / users API where parity exists.
"""

from __future__ import annotations

from src.frontend_gateway.protocol import BackendClient
from src.frontend_gateway.settings import (
    FrontendBackendSettings,
    load_frontend_backend_settings,
    use_http_backend_client,
)


def get_backend_client() -> BackendClient:
    """Return the process- or session-scoped :class:`BackendClient` (in-process or HTTP)."""
    from src.core.app_state import get_backend_client as _core_get_backend_client

    return _core_get_backend_client()


def get_frontend_backend_settings() -> FrontendBackendSettings:
    """Resolved Streamlit backend configuration (cached)."""
    return load_frontend_backend_settings()


def is_http_backend_mode() -> bool:
    """True when Streamlit should call FastAPI (``RAGCRAFT_BACKEND_CLIENT=http`` and similar)."""
    return use_http_backend_client()
