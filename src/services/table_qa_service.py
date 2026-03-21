from __future__ import annotations

from src.domain.query_intent import QueryIntent


class TableQAService:
    """
    Small helper for table-aware QA: when to prioritize table assets and what to tell the LLM.

    Classification of table-oriented queries may come from QueryIntent.TABLE and/or question cues
    (e.g. comparison queries that explicitly reference tables/rows/columns).
    """

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

    def is_table_query(self, *, query_intent: QueryIntent, question: str) -> bool:
        if query_intent is QueryIntent.TABLE:
            return True

        raw = (question or "").strip()
        if not raw:
            return False

        q = " ".join(raw.lower().split())

        for phrase in self._QUESTION_TABLE_PHRASES:
            if phrase in q:
                return True

        if query_intent is QueryIntent.COMPARISON and any(
            token in q for token in ("table", "row", "column")
        ):
            return True

        return False

    def table_priority_boost(self) -> float:
        """Additive rerank score bump for table assets when table QA mode is on (cross-encoder scale)."""
        return 0.35

    def build_table_prompt_hint(self) -> str:
        return (
            "Table-focused question: use each asset's structured table excerpt when present "
            "(clear headers and rows); fall back to raw HTML or table text if needed. "
            "Compare rows or columns carefully when the question asks for comparison, ranking, "
            "highest/lowest, totals, averages, or percentages. "
            "Do not invent numbers or cells that are not clearly present in the provided table context; "
            "if the context is insufficient, say so. When your evidence is from a table asset, say so explicitly "
            "and cite using the given labels."
        )
