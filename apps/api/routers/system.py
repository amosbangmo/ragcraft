"""Liveness and service metadata (no domain logic)."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends

from apps.api.config import ApiSettings, get_settings
from apps.api.schemas.system import HealthResponse, VersionResponse

router = APIRouter(tags=["system"])


@router.get("/health", response_model=HealthResponse, summary="Liveness probe")
def health() -> HealthResponse:
    return HealthResponse()


@router.get("/version", response_model=VersionResponse, summary="API name and version")
def version(
    settings: Annotated[ApiSettings, Depends(get_settings)],
) -> VersionResponse:
    return VersionResponse(service=settings.api_title, version=settings.api_version)
