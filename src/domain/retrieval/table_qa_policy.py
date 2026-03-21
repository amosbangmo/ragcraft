"""Table-aware QA heuristics (pure rules and static prompt text)."""

from __future__ import annotations

from src.domain.query_intent import QueryIntent

_QUESTION_TABLE_PHRASES = (
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

TABLE_QA_RERANK_BOOST = 0.35

TABLE_QA_PROMPT_HINT = (
    "Table-focused question: use each asset's structured table excerpt when present "
    "(clear headers and rows); fall back to raw HTML or table text if needed. "
    "Compare rows or columns carefully when the question asks for comparison, ranking, "
    "highest/lowest, totals, averages, or percentages. "
    "Do not invent numbers or cells that are not clearly present in the provided table context; "
    "if the context is insufficient, say so. When your evidence is from a table asset, say so explicitly "
    "and cite using the given labels."
)


def is_table_focused_question(*, query_intent: QueryIntent, question: str) -> bool:
    if query_intent is QueryIntent.TABLE:
        return True

    raw = (question or "").strip()
    if not raw:
        return False

    q = " ".join(raw.lower().split())

    for phrase in _QUESTION_TABLE_PHRASES:
        if phrase in q:
            return True

    if query_intent is QueryIntent.COMPARISON and any(
        token in q for token in ("table", "row", "column")
    ):
        return True

    return False
