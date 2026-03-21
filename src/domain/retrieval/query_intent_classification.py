"""Heuristic query intent classification (pure rules, no I/O)."""

from __future__ import annotations

from src.domain.query_intent import QueryIntent

_TABLE_STRONG_PHRASES = (
    "what does the table",
    "what the table",
    "according to table",
    "according to the table",
    "which row",
    "which column",
    "compare the values",
    "final table",
    "in the table",
    "from the table",
    "table show",
    "table shows",
    "table say",
    "table says",
    "what does the table say",
)
_COMPARISON_MARKERS = (
    "compare",
    "comparison",
    "contrast",
    "difference between",
    "differences between",
    "better than",
    "which is better",
    "which one",
    "versus",
    " vs ",
    " vs.",
)
_TABLE_MARKERS = (
    "table",
    "row",
    "column",
    "spreadsheet",
    "pivot",
    "metric",
    "metrics",
    "value",
    "values",
    "score",
    "rank",
    "ranking",
    "highest",
    "lowest",
    "total",
    "average",
    "percentage",
    "percent",
)
_IMAGE_MARKERS = ("image", "figure", "diagram", "chart", "picture", "screenshot", "illustration")
_EXPLORATORY_MARKERS = (
    "overview",
    "summarize",
    "summarise",
    "tell me about",
    "everything about",
    "in general",
    "broadly",
    "explore",
    "background on",
    "context on",
    "what do we know about",
)
_FACTUAL_PREFIXES = (
    "who ",
    "what ",
    "when ",
    "where ",
    "which ",
    "how many ",
    "how much ",
    "list ",
    "define ",
    "name the",
)


def classify_query_intent(query: str | None) -> QueryIntent:
    """Failure-safe heuristic intent; returns UNKNOWN on empty input or unexpected errors."""
    try:
        return _classify_query_intent_inner(query)
    except Exception:
        return QueryIntent.UNKNOWN


def _classify_query_intent_inner(query: str | None) -> QueryIntent:
    raw = (query or "").strip()
    if not raw:
        return QueryIntent.UNKNOWN

    q = " ".join(raw.lower().split())

    for phrase in _TABLE_STRONG_PHRASES:
        if phrase in q:
            return QueryIntent.TABLE

    for marker in _COMPARISON_MARKERS:
        if marker in q:
            return QueryIntent.COMPARISON

    for marker in _TABLE_MARKERS:
        if marker in q:
            return QueryIntent.TABLE

    for marker in _IMAGE_MARKERS:
        if marker in q:
            return QueryIntent.IMAGE

    for marker in _EXPLORATORY_MARKERS:
        if marker in q:
            return QueryIntent.EXPLORATORY

    words = q.split()
    word_count = len(words)
    if word_count >= 25 or len(q) >= 200:
        return QueryIntent.EXPLORATORY

    if word_count <= 18 and (
        q.endswith("?") or any(q.startswith(p) for p in _FACTUAL_PREFIXES)
    ):
        return QueryIntent.FACTUAL

    if word_count <= 12 and len(q) <= 72:
        return QueryIntent.FACTUAL

    return QueryIntent.UNKNOWN
