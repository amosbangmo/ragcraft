"""
Validated partial overrides for per-request retrieval tuning.

Used on RAG orchestration boundaries instead of raw ``dict[str, Any]``. Keys must match
:class:`~domain.retrieval_settings.RetrievalSettings` (same allowlist as
:class:`~application.settings.retrieval_settings_tuner.RetrievalSettingsTuner.merge`).
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, fields
from typing import Any


@dataclass(frozen=True, slots=True)
class RetrievalSettingsOverrideSpec:
    """Immutable overrides merged onto project/effective :class:`~domain.retrieval_settings.RetrievalSettings`."""

    _patch: tuple[tuple[str, Any], ...]

    @classmethod
    def from_optional_mapping(cls, raw: Mapping[str, Any] | None) -> RetrievalSettingsOverrideSpec | None:
        if raw is None or len(raw) == 0:
            return None
        from domain.rag.retrieval_settings import RetrievalSettings

        allowed = {f.name for f in fields(RetrievalSettings)}
        unknown = set(raw) - allowed
        if unknown:
            raise ValueError(f"Unknown retrieval setting keys: {sorted(unknown)}")
        items = tuple(sorted(raw.items(), key=lambda kv: kv[0]))
        return cls(_patch=items)

    def as_merge_mapping(self) -> dict[str, Any]:
        return dict(self._patch)
