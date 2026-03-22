"""
Deterministic metrics for citations that appear in the **generated answer** text.

Maps bracketed labels like ``[Source 1]`` to ``doc_id`` via the pipeline's
``prompt_sources`` list (``source_number`` / list order, ``doc_id``).
"""

from __future__ import annotations

import re
from typing import Any

# Conservative: only treat explicit "[Source N]" markers as citations.
# Matches instructions in ``PromptBuilderService.build_prompt`` (e.g. "[Source 1]", "[Source 2][Table: ...]").
_SOURCE_LABEL_RE = re.compile(r"\[\s*Source\s+(\d+)\s*\]", re.IGNORECASE)


def extract_cited_source_numbers(answer: str) -> set[int]:
    """Return distinct source indices cited in the answer (1-based)."""
    if not answer or not isinstance(answer, str):
        return set()
    found: set[int] = set()
    for m in _SOURCE_LABEL_RE.finditer(answer):
        try:
            found.add(int(m.group(1)))
        except (TypeError, ValueError):
            continue
    return found


def build_source_number_to_ref(prompt_sources: list[Any]) -> dict[int, dict[str, Any]]:
    """
    Map 1-based source index to prompt source dict.

    Uses ``source_number`` when present; otherwise falls back to list position (1..n).
    """
    out: dict[int, dict[str, Any]] = {}
    if not isinstance(prompt_sources, list):
        return out
    for idx, ref in enumerate(prompt_sources):
        if not isinstance(ref, dict):
            continue
        raw_n = ref.get("source_number")
        if raw_n is not None:
            try:
                n = int(raw_n)
            except (TypeError, ValueError):
                n = idx + 1
        else:
            n = idx + 1
        out[n] = ref
    return out


def answer_cited_doc_ids(*, answer: str, prompt_sources: list[Any]) -> set[str]:
    """Distinct ``doc_id`` values for sources explicitly cited in ``answer``."""
    numbers = extract_cited_source_numbers(answer)
    by_n = build_source_number_to_ref(prompt_sources)
    doc_ids: set[str] = set()
    for n in numbers:
        ref = by_n.get(n)
        if not ref:
            continue
        did = ref.get("doc_id")
        if did:
            doc_ids.add(str(did))
    return doc_ids
