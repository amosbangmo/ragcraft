"""
Cross-cutting HTTP wire types shared by multiple routers/schemas.

Re-exports stable :class:`typing.TypedDict` shapes from :mod:`interfaces.http.schemas.plain_payloads`
so callers can depend on a single module for common JSON contracts.
"""

from __future__ import annotations

from interfaces.http.schemas.plain_payloads import (
    PromptSourceJson,
    RawAssetJson,
    SourceDocumentJson,
)

__all__ = [
    "PromptSourceJson",
    "RawAssetJson",
    "SourceDocumentJson",
]
