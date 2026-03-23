"""
FastAPI entrypoint for RAGCraft.

Run locally (from repository root, with ``src`` on ``PYTHONPATH``)::

    uvicorn apps.api.main:app --reload --host 127.0.0.1 --port 8000

Windows PowerShell::

    $env:PYTHONPATH = (Get-Location).Path
    python -m uvicorn apps.api.main:app --reload --host 127.0.0.1 --port 8000
"""

from __future__ import annotations

from fastapi import FastAPI

from interfaces.http.config import load_settings
from interfaces.http.error_handlers import register_exception_handlers
from interfaces.http.openapi_common import build_openapi_schema
from interfaces.http.routers import auth, chat, evaluation, projects, system, users

_API_DESCRIPTION = """\
RAGCraft HTTP API for workspaces, RAG chat, evaluation flows, and user profile data.

**Identity:** obtain a JWT from ``POST /auth/login`` or ``/auth/register``, then send
``Authorization: Bearer <access_token>`` on user-scoped routes (projects, chat, evaluation,
``/users/me``). ``GET /health`` and ``GET /version`` are public.

**Errors:** JSON error bodies use a stable envelope — ``detail``, ``message``, ``error_type``,
``code``, ``category`` — see ``CanonicalApiError`` in this schema and ``apps.api.error_payload``.
"""


def create_app() -> FastAPI:
    settings = load_settings()
    app = FastAPI(
        title=settings.api_title,
        version=settings.api_version,
        description=_API_DESCRIPTION,
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_tags=[
            {
                "name": "chat",
                "description": "RAG turns, pipeline inspection, summary recall preview, retrieval comparison.",
            },
            {
                "name": "projects",
                "description": "Projects, documents, ingest/reindex, retrieval settings, cache invalidation.",
            },
            {
                "name": "evaluation",
                "description": "Manual eval, gold QA benchmarks, QA dataset CRUD, query logs, benchmark export.",
            },
            {
                "name": "users",
                "description": "Profile and account APIs (SQLite-backed); require Bearer JWT.",
            },
            {
                "name": "auth",
                "description": "Login and registration; returns JWT ``access_token`` plus profile.",
            },
            {"name": "system", "description": "Liveness and version metadata (no auth header)."},
        ],
    )

    def custom_openapi():
        if app.openapi_schema:
            return app.openapi_schema
        app.openapi_schema = build_openapi_schema(
            app_title=app.title,
            app_version=app.version,
            app_description=app.description or "",
            routes=app.routes,
        )
        return app.openapi_schema

    app.openapi = custom_openapi  # type: ignore[method-assign]

    register_exception_handlers(app)
    app.include_router(system.router)
    app.include_router(auth.router)
    app.include_router(chat.router)
    app.include_router(projects.router)
    app.include_router(evaluation.router)
    app.include_router(users.router)
    return app


app = create_app()
