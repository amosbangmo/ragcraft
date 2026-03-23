"""Map exceptions to predictable HTTP responses; log internal details, never stack traces to clients."""

from __future__ import annotations

import logging
from typing import Any

from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from interfaces.http.error_payload import api_error_body
from infrastructure.config.exceptions import RAGCraftError

logger = logging.getLogger("ragcraft.api.exceptions")


def _json_response(status_code: int, body: dict[str, Any]) -> JSONResponse:
    return JSONResponse(status_code=status_code, content=body)


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(RequestValidationError)
    async def _validation_error(request: Request, exc: RequestValidationError) -> JSONResponse:
        logger.debug("Request validation failed: %s", exc.errors())
        body = api_error_body(
            message="Request validation failed.",
            error_type="RequestValidationError",
            code="request_validation_failed",
            category="transport",
        )
        body["detail"] = exc.errors()
        return _json_response(422, body)

    @app.exception_handler(HTTPException)
    async def _http_exception(request: Request, exc: HTTPException) -> JSONResponse:
        detail = exc.detail
        if exc.status_code >= 500:
            logger.error(
                "HTTPException %s detail=%r path=%s",
                exc.status_code,
                exc.detail,
                request.url.path,
            )
        if isinstance(detail, str):
            return _json_response(
                exc.status_code,
                api_error_body(
                    message=detail,
                    error_type="HTTPException",
                    code=f"http_{exc.status_code}",
                    category="transport",
                ),
            )
        return _json_response(
            exc.status_code,
            api_error_body(
                message="Request failed.",
                error_type="HTTPException",
                code=f"http_{exc.status_code}",
                category="transport",
                extra={"errors" if isinstance(detail, list) else "context": detail},
            ),
        )

    @app.exception_handler(ValueError)
    async def _value_error(request: Request, exc: ValueError) -> JSONResponse:
        message = str(exc) or "Invalid request."
        logger.info("ValueError: %s path=%s", message, request.url.path)
        not_found = "not found" in message.lower()
        status = 404 if not_found else 400
        return _json_response(
            status,
            api_error_body(
                message=message,
                error_type="ValueError",
                code="resource_not_found" if not_found else "invalid_argument",
                category="application",
            ),
        )

    @app.exception_handler(RuntimeError)
    async def _runtime_error(request: Request, exc: RuntimeError) -> JSONResponse:
        logger.exception("RuntimeError path=%s", request.url.path)
        return _json_response(
            500,
            api_error_body(
                message="An internal error occurred.",
                error_type="RuntimeError",
                code="internal_error",
                category="internal",
            ),
        )

    @app.exception_handler(FileNotFoundError)
    async def _file_not_found(request: Request, exc: FileNotFoundError) -> JSONResponse:
        message = str(exc) or "Resource not found."
        logger.info("FileNotFoundError: %s path=%s", message, request.url.path)
        return _json_response(
            404,
            api_error_body(
                message=message,
                error_type="FileNotFoundError",
                code="resource_not_found",
                category="application",
            ),
        )

    @app.exception_handler(RAGCraftError)
    async def _ragcraft_error(request: Request, exc: RAGCraftError) -> JSONResponse:
        status = exc.http_status()
        layer = type(exc).layer
        logger.log(
            logging.ERROR if status >= 500 else logging.WARNING,
            "%s [%s] layer=%s status=%s internal=%r path=%s",
            type(exc).__name__,
            exc.resolved_error_code,
            layer,
            status,
            exc.internal_message,
            request.url.path,
        )
        return _json_response(
            status,
            api_error_body(
                message=exc.user_message,
                error_type=type(exc).__name__,
                code=exc.resolved_error_code,
                category=layer,
            ),
        )
