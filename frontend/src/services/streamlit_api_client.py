"""
Streamlit ↔ backend boundary: one entrypoint for :class:`~services.protocol.BackendClient`.

Pages obtain the client via :func:`get_backend_client` from this module or
:mod:`services.streamlit_context` (same implementation). Do not import
the composition root or service containers from feature code.

Modes (environment)
-------------------

``RAGCRAFT_BACKEND_CLIENT``
    * ``http`` (default), ``api``, or ``remote`` — calls the FastAPI app via
      :class:`~services.http_client.HttpBackendClient`.
    * ``in_process`` — same Python process as Streamlit (no uvicorn); uses
      :class:`~services.in_process.InProcessBackendClient`.

``RAGCRAFT_API_BASE_URL``
    Root URL without trailing slash, e.g. ``http://127.0.0.1:8000``.

``RAGCRAFT_API_CONNECT_TIMEOUT_SECONDS`` (default ``10``)
    Connection timeout.

``RAGCRAFT_API_READ_TIMEOUT_SECONDS``
    Read timeout for long requests. If unset, ``RAGCRAFT_API_TIMEOUT_SECONDS`` is used (default ``300``).

Vertical slices already wired through ``BackendClient`` (projects list/create, chat ask, pipeline
inspect, gold QA dataset run, exports, etc.) automatically use FastAPI when HTTP mode is enabled —
no per-page branching required.

Login/register and session reads for Streamlit go through :mod:`services.streamlit_auth`
(HTTP mode uses ``/auth/login`` and ``/auth/register``). Profile mutations use :class:`~services.protocol.BackendClient` and
:func:`~services.streamlit_context.refresh_streamlit_auth_session_from_user_id`.

Streamlit pages gateway checklist (business I/O via :func:`get_backend_client` / ``BackendClient``)
---------------------------------------------------------------------------------------------------
* ``frontend/app.py`` — shell only (no backend calls).
* ``frontend/src/pages/login.py`` — :mod:`services.streamlit_auth` (not ``BackendClient``).
* ``frontend/src/pages/projects.py``, ``ingestion.py`` — projects + documents + table actions.
* ``frontend/src/pages/chat.py`` — ``ask_question``, ``invalidate_project_chain``, chat session stubs on client.
* ``frontend/src/pages/search.py`` — ``search_project_summaries``.
* ``frontend/src/pages/retrieval_inspector.py`` — ``inspect_retrieval``, ``preview_summary_recall``.
* ``frontend/src/pages/retrieval_comparison.py`` — ``compare_retrieval_modes``.
* ``frontend/src/pages/evaluation.py`` + ``frontend/src/components/shared/evaluation_*.py`` — manual/dataset/gold/retrieval tabs via client.
* ``frontend/src/pages/profile.py`` — client profile/password/avatar/delete + session refresh helper.

The optional in-process mode builds an :class:`~services.in_process.InProcessBackendClient`
over a cached :class:`~composition.BackendApplicationContainer` inside :mod:`infrastructure.config.app_state` only.
"""

from __future__ import annotations

from services.protocol import BackendClient
from services.settings import (
    FrontendBackendSettings,
    load_frontend_backend_settings,
    use_http_backend_client,
)


def get_backend_client() -> BackendClient:
    """Return the process- or session-scoped :class:`BackendClient` (in-process or HTTP)."""
    from infrastructure.config.app_state import get_backend_client as _core_get_backend_client

    return _core_get_backend_client()


def get_frontend_backend_settings() -> FrontendBackendSettings:
    """Resolved Streamlit backend configuration (cached)."""
    return load_frontend_backend_settings()


def is_http_backend_mode() -> bool:
    """True when Streamlit should call FastAPI (``RAGCRAFT_BACKEND_CLIENT=http`` and similar)."""
    return use_http_backend_client()
