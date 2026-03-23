from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any

from infrastructure.config.config import RETRIEVAL_CONFIG, RetrievalConfig


@dataclass(frozen=True)
class RetrievalSettings:
    """
    Strongly typed, per-query retrieval tuning surface.

    Defaults mirror ``RetrievalConfig`` / ``RETRIEVAL_CONFIG`` (env-backed).
    """

    enable_query_rewrite: bool
    enable_hybrid_retrieval: bool
    similarity_search_k: int
    bm25_search_k: int
    hybrid_search_k: int
    max_prompt_assets: int
    bm25_k1: float
    bm25_b: float
    bm25_epsilon: float
    rrf_k: int
    hybrid_beta: float
    max_text_chars_per_asset: int
    max_table_chars_per_asset: int
    query_rewrite_max_history_messages: int
    enable_contextual_compression: bool
    enable_section_expansion: bool
    section_expansion_neighbor_window: int
    section_expansion_max_per_section: int
    section_expansion_global_max: int

    @classmethod
    def from_retrieval_config(cls, cfg: RetrievalConfig) -> RetrievalSettings:
        return cls(
            enable_query_rewrite=bool(cfg.enable_query_rewrite),
            enable_hybrid_retrieval=bool(cfg.enable_hybrid_retrieval),
            similarity_search_k=int(cfg.similarity_search_k),
            bm25_search_k=int(cfg.bm25_search_k),
            hybrid_search_k=int(cfg.hybrid_search_k),
            max_prompt_assets=int(cfg.max_prompt_assets),
            bm25_k1=float(cfg.bm25_k1),
            bm25_b=float(cfg.bm25_b),
            bm25_epsilon=float(cfg.bm25_epsilon),
            rrf_k=int(cfg.rrf_k),
            hybrid_beta=float(cfg.hybrid_beta),
            max_text_chars_per_asset=int(cfg.max_text_chars_per_asset),
            max_table_chars_per_asset=int(cfg.max_table_chars_per_asset),
            query_rewrite_max_history_messages=int(cfg.query_rewrite_max_history_messages),
            enable_contextual_compression=bool(cfg.enable_contextual_compression),
            enable_section_expansion=bool(cfg.enable_section_expansion),
            section_expansion_neighbor_window=int(cfg.section_expansion_neighbor_window),
            section_expansion_max_per_section=int(cfg.section_expansion_max_per_section),
            section_expansion_global_max=int(cfg.section_expansion_global_max),
        )

    @classmethod
    def from_object(cls, obj: Any) -> RetrievalSettings:
        """
        Build settings from a ``RetrievalConfig`` or any object exposing the same
        attributes (used by tests with a mutable namespace).
        """
        if isinstance(obj, RetrievalConfig):
            return cls.from_retrieval_config(obj)
        kwargs: dict[str, Any] = {}
        template = cls.from_retrieval_config(RETRIEVAL_CONFIG)
        for key, template_value in asdict(template).items():
            if hasattr(obj, key):
                kwargs[key] = getattr(obj, key)
            else:
                kwargs[key] = template_value
        return cls(**kwargs)

    def to_log_dict(self) -> dict[str, Any]:
        """Flat dict for structured logging (no secrets)."""
        return asdict(self)
