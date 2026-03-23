"""Small response models for unauthenticated metadata routes (generator-friendly OpenAPI)."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class HealthResponse(BaseModel):
    model_config = {"extra": "forbid"}

    status: Literal["ok"] = Field(
        default="ok",
        description="Process is accepting requests.",
    )


class VersionResponse(BaseModel):
    model_config = {"extra": "forbid"}

    service: str = Field(description="Product name from API settings.")
    version: str = Field(description="Semantic or build version string.")
