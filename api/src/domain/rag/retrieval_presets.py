from __future__ import annotations

from enum import Enum


class RetrievalPreset(str, Enum):
    """Standard retrieval modes (string values are stable API / session keys)."""

    PRECISE = "precise"
    BALANCED = "balanced"
    EXPLORATORY = "exploratory"


# Low k for precise mode (precision over recall).
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
    """
    Normalize user/session input to a preset.

    Accepts enum members, canonical values (``precise`` / ``balanced`` / ``exploratory``),
    legacy title-case labels from older UI, or unknown strings (falls back to balanced).
    """
    if isinstance(value, RetrievalPreset):
        return value
    if value is None or not str(value).strip():
        return RetrievalPreset.BALANCED
    raw = str(value).strip()
    lowered = raw.lower()
    for p in RetrievalPreset:
        if lowered == p.value or lowered == p.name.lower():
            return p
    # Legacy Streamlit labels: "Precise", "Balanced", "Exploratory"
    for p in RetrievalPreset:
        if raw == PRESET_UI_LABELS[p]:
            return p
    return RetrievalPreset.BALANCED
