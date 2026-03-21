"""Map domain / application exceptions to HTTP responses."""

from __future__ import annotations

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from src.core.exceptions import DocStoreError, LLMServiceError, RAGCraftError, VectorStoreError


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(RequestValidationError)
    async def _validation_error(request: Request, exc: RequestValidationError) -> JSONResponse:
        return JSONResponse(
            status_code=422,
            content={
                "error_type": "validation_error",
                "detail": exc.errors(),
            },
        )

    @app.exception_handler(ValueError)
    async def _value_error(request: Request, exc: ValueError) -> JSONResponse:
        message = str(exc) or "Invalid request."
        not_found = "not found" in message.lower()
        return JSONResponse(
            status_code=404 if not_found else 400,
            content={
                "error_type": "ValueError",
                "detail": message,
            },
        )

    @app.exception_handler(RuntimeError)
    async def _runtime_error(request: Request, exc: RuntimeError) -> JSONResponse:
        return JSONResponse(
            status_code=500,
            content={
                "error_type": "RuntimeError",
                "detail": str(exc) or "Internal server error.",
            },
        )

    @app.exception_handler(FileNotFoundError)
    async def _file_not_found(request: Request, exc: FileNotFoundError) -> JSONResponse:
        return JSONResponse(
            status_code=404,
            content={
                "detail": str(exc) or "Resource not found.",
                "error_type": "FileNotFoundError",
            },
        )

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
