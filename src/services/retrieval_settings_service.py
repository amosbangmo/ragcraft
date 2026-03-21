from __future__ import annotations

from dataclasses import fields, replace
from typing import Any

from src.core.config import RETRIEVAL_CONFIG, RetrievalConfig
from src.domain.retrieval_settings import RetrievalSettings


class RetrievalSettingsService:
    """
    Central place for default retrieval tuning, merge overrides, and validation.

    ``config_source`` is usually ``RETRIEVAL_CONFIG``; tests may swap in a mutable
    object with the same attributes.
    """

    def __init__(self, config_source: RetrievalConfig | Any | None = None) -> None:
        self._config_source: RetrievalConfig | Any = (
            RETRIEVAL_CONFIG if config_source is None else config_source
        )

    @property
    def config_source(self) -> RetrievalConfig | Any:
        return self._config_source

    def set_config_source(self, source: RetrievalConfig | Any) -> None:
        self._config_source = source

    def get_default(self) -> RetrievalSettings:
        return RetrievalSettings.from_object(self._config_source)

    def merge(
        self,
        base: RetrievalSettings,
        override: dict[str, Any] | None,
    ) -> RetrievalSettings:
        if not override:
            return self.validate(base)

        allowed = {f.name for f in fields(RetrievalSettings)}
        unknown = set(override) - allowed
        if unknown:
            raise ValueError(f"Unknown retrieval setting keys: {sorted(unknown)}")

        coerced: dict[str, Any] = dict(override)
        for key, raw in list(coerced.items()):
            coerced[key] = self._coerce_field(key, raw)

        merged = replace(base, **coerced)
        return self.validate(merged)

    def validate(self, settings: RetrievalSettings) -> RetrievalSettings:
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
