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

from apps.api.config import load_settings
from apps.api.error_handlers import register_exception_handlers
from apps.api.routers import chat, evaluation, projects, system, users


def create_app() -> FastAPI:
    settings = load_settings()
    app = FastAPI(
        title=settings.api_title,
        version=settings.api_version,
        docs_url="/docs",
        redoc_url="/redoc",
    )
    register_exception_handlers(app)
    app.include_router(system.router)
    app.include_router(chat.router)
    app.include_router(projects.router)
    app.include_router(evaluation.router)
    app.include_router(users.router)
    return app


app = create_app()
