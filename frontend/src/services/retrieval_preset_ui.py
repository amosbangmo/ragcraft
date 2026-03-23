"""Retrieval preset labels and parsing (wire-stable enum values)."""

from __future__ import annotations

from enum import Enum


class RetrievalPreset(str, Enum):
    PRECISE = "precise"
    BALANCED = "balanced"
    EXPLORATORY = "exploratory"


PRECISE_SEARCH_K = 8

PRESET_DESCRIPTIONS: dict[RetrievalPreset, str] = {
    RetrievalPreset.PRECISE: (
        "High precision, minimal noise: query rewrite on, vector-only recall, smaller candidate pool."
    ),
    RetrievalPreset.BALANCED: (
        "Default trade-off: query rewrite and hybrid (semantic + keyword) search with medium breadth."
    ),
    RetrievalPreset.EXPLORATORY: (
        "Maximize recall and discovery: hybrid on, larger k, query rewrite off for broader matching."
    ),
}

PRESET_UI_LABELS: dict[RetrievalPreset, str] = {
    RetrievalPreset.PRECISE: "Precise",
    RetrievalPreset.BALANCED: "Balanced",
    RetrievalPreset.EXPLORATORY: "Exploratory",
}

PRESET_SELECT_ORDER: tuple[RetrievalPreset, ...] = (
    RetrievalPreset.PRECISE,
    RetrievalPreset.BALANCED,
    RetrievalPreset.EXPLORATORY,
)


def parse_retrieval_preset(value: str | RetrievalPreset | None) -> RetrievalPreset:
    if isinstance(value, RetrievalPreset):
        return value
    if value is None or not str(value).strip():
        return RetrievalPreset.BALANCED
    raw = str(value).strip()
    lowered = raw.lower()
    for p in RetrievalPreset:
        if lowered == p.value or lowered == p.name.lower():
            return p
    for p in RetrievalPreset:
        if raw == PRESET_UI_LABELS[p]:
            return p
    return RetrievalPreset.BALANCED
