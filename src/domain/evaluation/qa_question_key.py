"""Pure helpers for comparing and deduplicating QA dataset questions."""

_PUNCT_STRIP = "?.!;:,"


def normalized_qa_question_key(question: str) -> str:
    """Lowercase, collapse whitespace, strip trailing sentence punctuation (matches prior behavior)."""
    normalized = " ".join((question or "").strip().lower().split())
    return normalized.rstrip(_PUNCT_STRIP)
