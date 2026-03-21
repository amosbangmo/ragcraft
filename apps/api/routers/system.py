"""Liveness and service metadata (no domain logic)."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends

from apps.api.config import ApiSettings, get_settings

router = APIRouter()


@router.get("/health", summary="Liveness probe")
def health() -> dict[str, str]:
    return {"status": "ok"}


@router.get("/version", summary="API name and version")
def version(
    settings: Annotated[ApiSettings, Depends(get_settings)],
) -> dict[str, str]:
    return {
        "service": settings.api_title,
        "version": settings.api_version,
    }
