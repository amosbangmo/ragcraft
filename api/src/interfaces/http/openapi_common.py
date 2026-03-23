"""Shared OpenAPI fragments: canonical error examples and schema enrichment for codegen-friendly docs."""

from __future__ import annotations

from typing import Any

from fastapi.openapi.utils import get_openapi
from starlette.routing import BaseRoute

_CANONICAL_ERROR_FIELDS: dict[str, Any] = {
    "detail": "Human-readable error (string for most errors; validation uses a structured list).",
    "message": "Same as detail when detail is a string.",
    "error_type": "Exception class name when applicable.",
    "code": "Stable machine identifier for this failure mode.",
    "category": "One of: domain, application, infrastructure, transport, internal.",
}

CANONICAL_ERROR_EXAMPLE: dict[str, Any] = {
    "detail": "Request could not be processed.",
    "message": "Request could not be processed.",
    "error_type": "ApplicationError",
    "code": "application_error",
    "category": "application",
}

VALIDATION_ERROR_EXAMPLE: dict[str, Any] = {
    "detail": [
        {
            "type": "missing",
            "loc": ["body", "project_id"],
            "msg": "Field required",
            "input": {},
        }
    ],
    "message": "Request validation failed.",
    "error_type": "RequestValidationError",
    "code": "request_validation_failed",
    "category": "transport",
}


def _json_example(example: dict[str, Any]) -> dict[str, Any]:
    return {"application/json": {"example": example}}


def openapi_error_response(
    *,
    description: str,
    example: dict[str, Any] | None = None,
) -> dict[str, Any]:
    return {
        "description": description,
        "content": _json_example(example or CANONICAL_ERROR_EXAMPLE),
    }


# Responses merged into route `responses=` for predictable client stubs.
COMMON_ERROR_RESPONSES: dict[int | str, dict[str, Any]] = {
    400: openapi_error_response(
        description="Malformed ``Authorization`` header, invalid arguments, or explicit HTTP 400.",
    ),
    401: openapi_error_response(
        description="Missing bearer token, invalid or expired JWT, or invalid credentials.",
        example={
            "detail": "Authentication required. Send Authorization: Bearer <token>.",
            "message": "Authentication required. Send Authorization: Bearer <token>.",
            "error_type": "AuthenticationRequiredError",
            "code": "authentication_required",
            "category": "application",
        },
    ),
    404: openapi_error_response(
        description="Resource not found or domain not-found mapped to HTTP 404.",
        example={
            **CANONICAL_ERROR_EXAMPLE,
            "detail": "Project not found.",
            "message": "Project not found.",
            "code": "http_404",
        },
    ),
    422: openapi_error_response(
        description="Request body or query validation failed (see ``detail`` list).",
        example=VALIDATION_ERROR_EXAMPLE,
    ),
    500: openapi_error_response(
        description="Unexpected server error (generic envelope; no stack traces).",
        example={
            **CANONICAL_ERROR_EXAMPLE,
            "detail": "An internal error occurred.",
            "message": "An internal error occurred.",
            "error_type": "RuntimeError",
            "code": "internal_error",
            "category": "internal",
        },
    ),
}


def upstream_error_responses() -> dict[int | str, dict[str, Any]]:
    """LLM / vector / docstore failures (domain-specific codes still use the canonical envelope)."""
    return {
        502: openapi_error_response(
            description="Upstream model or LLM call failure.",
            example={
                **CANONICAL_ERROR_EXAMPLE,
                "detail": "Model invocation failed.",
                "message": "Model invocation failed.",
                "code": "http_502",
            },
        ),
        503: openapi_error_response(
            description="Vector store, document store, or infrastructure dependency failure.",
            example={
                **CANONICAL_ERROR_EXAMPLE,
                "detail": "Vector store unavailable.",
                "message": "Vector store unavailable.",
                "code": "http_503",
            },
        ),
    }


def chat_route_responses() -> dict[int | str, dict[str, Any]]:
    out: dict[int | str, dict[str, Any]] = dict(COMMON_ERROR_RESPONSES)
    out.update(upstream_error_responses())
    return out


def enrich_openapi_schema(schema: dict[str, Any]) -> dict[str, Any]:
    """
    Enrich OpenAPI with shared documentation.

    Bearer JWT security is declared per-route via :class:`fastapi.security.HTTPBearer` dependencies
    (``HTTPBearer`` appears under ``components.securitySchemes`` automatically).
    """
    components = schema.setdefault("components", {})
    sec = components.setdefault("securitySchemes", {})
    sec.setdefault(
        "BearerAuth",
        {
            "type": "http",
            "scheme": "bearer",
            "bearerFormat": "JWT",
            "description": (
                "Workspace access token from ``POST /auth/login`` or ``POST /auth/register``. "
                "Send on user-scoped routes (projects, chat, evaluation, ``/users/me``)."
            ),
        },
    )
    # Document canonical error shape once under components.schemas for Redoc/IDE tooling.
    schemas = components.setdefault("schemas", {})
    if "CanonicalApiError" not in schemas:
        schemas["CanonicalApiError"] = {
            "type": "object",
            "description": "Stable error envelope from ``interfaces.http.error_payload.api_error_body``.",
            "required": ["detail", "message", "error_type", "code", "category"],
            "properties": {
                "detail": {
                    "description": _CANONICAL_ERROR_FIELDS["detail"],
                    "oneOf": [
                        {"type": "string"},
                        {"type": "array", "items": {"type": "object"}},
                    ],
                },
                "message": {"type": "string", "description": _CANONICAL_ERROR_FIELDS["message"]},
                "error_type": {"type": "string"},
                "code": {"type": "string"},
                "category": {"type": "string"},
            },
        }
    return schema


def build_openapi_schema(
    *,
    app_title: str,
    app_version: str,
    app_description: str,
    routes: list[BaseRoute],
) -> dict[str, Any]:
    schema = get_openapi(
        title=app_title,
        version=app_version,
        description=app_description,
        routes=routes,
    )
    return enrich_openapi_schema(schema)
