"""Small shared strings for evaluation exports and UI (no Streamlit)."""


def format_bool_toggle_on_off(value: bool) -> str:
    """Human-readable on/off label used in Markdown reports and export summaries."""
    return "on" if value else "off"


BENCHMARK_MARKDOWN_NOTE_JUDGE_AGGREGATES = (
    "- Summary **LLM judge** averages (`avg_*` judge fields, `hallucination_rate`) exclude rows where "
    "`judge_failed` is true."
)
BENCHMARK_MARKDOWN_NOTE_PIPELINE_VS_JUDGE = (
    "- **`pipeline_failure_rate`** counts only rows where the answer pipeline did not complete "
    "(distinct from judge failures)."
)
BENCHMARK_MARKDOWN_NOTE_JUDGE_ROW_FIELDS = "- Per-row judge fields may be blank / `None` when the judge failed for that entry — that is not a score of zero."
