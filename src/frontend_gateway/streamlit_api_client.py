"""
Streamlit ↔ backend boundary: one entrypoint for :class:`~src.frontend_gateway.protocol.BackendClient`.

Pages and ``src/ui`` obtain the client via :func:`get_backend_client` from this module or
:mod:`src.frontend_gateway.streamlit_context` (same implementation). Do not import
the composition root or service containers from feature code.

Modes (environment)
-------------------

``RAGCRAFT_BACKEND_CLIENT``
    * ``http`` (default), ``api``, or ``remote`` — calls the FastAPI app via
      :class:`~src.frontend_gateway.http_client.HttpBackendClient`.
    * ``in_process`` — same Python process as Streamlit (no uvicorn); uses
      :class:`~src.frontend_gateway.in_process.InProcessBackendClient`.

``RAGCRAFT_API_BASE_URL``
    Root URL without trailing slash, e.g. ``http://127.0.0.1:8000``.

``RAGCRAFT_API_CONNECT_TIMEOUT_SECONDS`` (default ``10``)
    Connection timeout.

``RAGCRAFT_API_READ_TIMEOUT_SECONDS``
    Read timeout for long requests. If unset, ``RAGCRAFT_API_TIMEOUT_SECONDS`` is used (default ``300``).

Vertical slices already wired through ``BackendClient`` (projects list/create, chat ask, pipeline
inspect, gold QA dataset run, exports, etc.) automatically use FastAPI when HTTP mode is enabled —
no per-page branching required.

Login/register and session reads for Streamlit go through :mod:`src.frontend_gateway.streamlit_auth`
(HTTP mode uses ``/auth/login`` and ``/auth/register``). Profile mutations use :class:`~src.frontend_gateway.protocol.BackendClient` and
:func:`~src.frontend_gateway.streamlit_context.refresh_streamlit_auth_session_from_user_id`.

Streamlit pages gateway checklist (business I/O via :func:`get_backend_client` / ``BackendClient``)
---------------------------------------------------------------------------------------------------
* ``streamlit_app.py`` — shell only (no backend calls).
* ``pages/login.py`` — :mod:`src.frontend_gateway.streamlit_auth` (not ``BackendClient``).
* ``pages/projects.py``, ``pages/ingestion.py`` — projects + documents + table actions.
* ``pages/chat.py`` — ``ask_question``, ``invalidate_project_chain``, chat session stubs on client.
* ``pages/search.py`` — ``search_project_summaries``.
* ``pages/retrieval_inspector.py`` — ``inspect_retrieval``, ``preview_summary_recall``.
* ``pages/retrieval_comparison.py`` — ``compare_retrieval_modes``.
* ``pages/evaluation.py`` + ``src/ui/evaluation_*.py`` — manual/dataset/gold/retrieval tabs via client.
* ``pages/profile.py`` — client profile/password/avatar/delete + session refresh helper.

The optional in-process mode builds an :class:`~src.frontend_gateway.in_process.InProcessBackendClient`
over a cached :class:`~src.composition.BackendApplicationContainer` inside :mod:`src.core.app_state` only.
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
