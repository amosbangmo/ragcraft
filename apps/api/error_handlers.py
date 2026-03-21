"""Map domain / application exceptions to HTTP responses."""

from __future__ import annotations

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from src.core.exceptions import DocStoreError, LLMServiceError, RAGCraftError, VectorStoreError


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(RAGCraftError)
    async def _ragcraft_error(request: Request, exc: RAGCraftError) -> JSONResponse:
        status_code = 503
        if isinstance(exc, LLMServiceError):
            status_code = 502
        elif isinstance(exc, (VectorStoreError, DocStoreError)):
            status_code = 503
        return JSONResponse(
            status_code=status_code,
            content={
                "detail": exc.user_message,
                "error_type": type(exc).__name__,
            },
        )
