"""Preset → RetrievalSettingsPayload mapping for Streamlit (no domain types)."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import fields, replace
from typing import Any, Protocol, runtime_checkable

from infrastructure.config.config import RETRIEVAL_CONFIG, RetrievalConfig

from services.contract.api_contract_models import RetrievalSettingsPayload
from services.retrieval.retrieval_preset_ui import PRECISE_SEARCH_K, RetrievalPreset, parse_retrieval_preset


@runtime_checkable
class RetrievalPresetMergePort(Protocol):
    def from_preset(self, preset: str | RetrievalPreset) -> RetrievalSettingsPayload: ...

    def merge(
        self, base: RetrievalSettingsPayload, overrides: Mapping[str, Any]
    ) -> RetrievalSettingsPayload: ...


class RetrievalPresetMergeService:
    def __init__(self, config_source: RetrievalConfig | Any | None = None) -> None:
        self._config_source: RetrievalConfig | Any = (
            RETRIEVAL_CONFIG if config_source is None else config_source
        )

    def get_default(self) -> RetrievalSettingsPayload:
        return RetrievalSettingsPayload.from_retrieval_config(self._config_source)

    def from_preset(self, preset: str | RetrievalPreset) -> RetrievalSettingsPayload:
        p = parse_retrieval_preset(preset)
        base = self.get_default()

        if p == RetrievalPreset.BALANCED:
            return self.validate(
                replace(
                    base,
                    enable_query_rewrite=True,
                    enable_hybrid_retrieval=True,
                )
            )

        if p == RetrievalPreset.PRECISE:
            k = PRECISE_SEARCH_K
            return self.validate(
                replace(
                    base,
                    enable_query_rewrite=True,
                    enable_hybrid_retrieval=False,
                    similarity_search_k=k,
                    bm25_search_k=k,
                    hybrid_search_k=k,
                )
            )

        k = max(30, int(base.similarity_search_k * 1.5))
        return self.validate(
            replace(
                base,
                enable_query_rewrite=False,
                enable_hybrid_retrieval=True,
                similarity_search_k=k,
                bm25_search_k=max(base.bm25_search_k, k),
                hybrid_search_k=max(base.hybrid_search_k, k),
            )
        )

    def merge(
        self,
        base: RetrievalSettingsPayload,
        override: Mapping[str, Any] | dict[str, Any] | None = None,
    ) -> RetrievalSettingsPayload:
        if not override:
            return self.validate(base)

        allowed = {f.name for f in fields(RetrievalSettingsPayload)}
        unknown = set(override) - allowed
        if unknown:
            raise ValueError(f"Unknown retrieval setting keys: {sorted(unknown)}")

        coerced: dict[str, Any] = dict(override)
        for key, raw in list(coerced.items()):
            coerced[key] = self._coerce_field(key, raw)

        merged = replace(base, **coerced)
        return self.validate(merged)

    def validate(self, settings: RetrievalSettingsPayload) -> RetrievalSettingsPayload:
        if settings.similarity_search_k < 1:
            raise ValueError("similarity_search_k must be >= 1")
        if settings.bm25_search_k < 1:
            raise ValueError("bm25_search_k must be >= 1")
        if settings.hybrid_search_k < 1:
            raise ValueError("hybrid_search_k must be >= 1")
        if settings.max_prompt_assets < 1:
            raise ValueError("max_prompt_assets must be >= 1")
        if settings.rrf_k < 1:
            raise ValueError("rrf_k must be >= 1")
        if settings.query_rewrite_max_history_messages < 0:
            raise ValueError("query_rewrite_max_history_messages must be >= 0")
        if settings.section_expansion_neighbor_window < 0:
            raise ValueError("section_expansion_neighbor_window must be >= 0")
        if settings.section_expansion_max_per_section < 1:
            raise ValueError("section_expansion_max_per_section must be >= 1")
        if settings.section_expansion_global_max < 1:
            raise ValueError("section_expansion_global_max must be >= 1")
        if settings.max_text_chars_per_asset < 1:
            raise ValueError("max_text_chars_per_asset must be >= 1")
        if settings.max_table_chars_per_asset < 1:
            raise ValueError("max_table_chars_per_asset must be >= 1")
        if settings.bm25_k1 <= 0:
            raise ValueError("bm25_k1 must be > 0")
        if not (0.0 <= settings.bm25_b <= 1.0):
            raise ValueError("bm25_b must be in [0, 1]")
        if settings.bm25_epsilon < 0:
            raise ValueError("bm25_epsilon must be >= 0")
        if not (0.0 <= settings.hybrid_beta <= 1.0):
            raise ValueError("hybrid_beta must be in [0, 1]")
        return settings

    def _coerce_field(self, key: str, raw: Any) -> Any:
        if key.startswith("enable_"):
            if isinstance(raw, bool):
                return raw
            if isinstance(raw, str):
                return raw.strip().lower() in {"1", "true", "yes", "on"}
            return bool(raw)
        if key in {"bm25_k1", "bm25_b", "bm25_epsilon", "hybrid_beta"}:
            return float(raw)
        return int(raw)


def default_retrieval_preset_merge_port() -> RetrievalPresetMergePort:
    return RetrievalPresetMergeService()
