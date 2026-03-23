"""Tests for :mod:`domain.rag.retrieval.section_expansion_rules`."""

from __future__ import annotations

from domain.rag.retrieval.section_expansion_rules import (
    anchor_cap_key,
    element_span,
    eligible_expansion_pair,
    expansion_distance,
    has_expansion_signals,
    page_span,
    pages_overlap,
)


def _asset(
    *,
    source_file: str = "a.pdf",
    section_id: str | None = None,
    chunk_title: str | None = None,
    section_title: str | None = None,
    start: int | None = None,
    end: int | None = None,
    page_number: int | None = None,
    page_start: int | None = None,
    page_end: int | None = None,
) -> dict:
    meta: dict = {}
    if section_id is not None:
        meta["section_id"] = section_id
    if chunk_title is not None:
        meta["chunk_title"] = chunk_title
    if section_title is not None:
        meta["section_title"] = section_title
    if start is not None and end is not None:
        meta["start_element_index"] = start
        meta["end_element_index"] = end
    if page_number is not None:
        meta["page_number"] = page_number
    if page_start is not None:
        meta["page_start"] = page_start
    if page_end is not None:
        meta["page_end"] = page_end
    return {"source_file": source_file, "metadata": meta}


def test_element_span_swaps_inverted_range() -> None:
    assert element_span(_asset(start=5, end=2)) == (2, 5)


def test_element_span_invalid_returns_none() -> None:
    assert element_span(_asset(start="x", end=1)) is None
    assert element_span(_asset(start=1, end=None)) is None


def test_page_span_from_range_and_single_page() -> None:
    assert page_span(_asset(page_start=3, page_end=1)) == (1, 3)
    assert page_span(_asset(page_number=7)) == (7, 7)


def test_page_span_invalid_page_number() -> None:
    a = _asset()
    a["metadata"]["page_number"] = "bad"
    assert page_span(a) is None


def test_pages_overlap() -> None:
    assert pages_overlap((1, 2), (2, 3)) is True
    assert pages_overlap((1, 2), (4, 5)) is False
    assert pages_overlap(None, (1, 2)) is False


def test_has_expansion_signals() -> None:
    assert has_expansion_signals(_asset(section_id="s1")) is True
    assert has_expansion_signals(_asset(start=0, end=1)) is True
    assert has_expansion_signals(_asset(page_number=1)) is True
    bare = {"source_file": "x.pdf", "metadata": {}}
    assert has_expansion_signals(bare) is False


def test_anchor_cap_key_priority() -> None:
    seed = _asset(source_file="f.pdf", section_id="A", chunk_title="ct")
    assert anchor_cap_key(seed).startswith("sid:")


def test_eligible_expansion_same_section() -> None:
    s = _asset(source_file="f.pdf", section_id="1")
    c = _asset(source_file="f.pdf", section_id="1")
    assert eligible_expansion_pair(s, c, neighbor_window=2) is True


def test_eligible_expansion_different_file() -> None:
    s = _asset(source_file="a.pdf", section_id="1")
    c = _asset(source_file="b.pdf", section_id="1")
    assert eligible_expansion_pair(s, c, neighbor_window=2) is False


def test_eligible_expansion_no_signals_on_seed() -> None:
    seed = {"source_file": "f.pdf", "metadata": {}}
    cand = _asset(source_file="f.pdf", section_id="1")
    assert eligible_expansion_pair(seed, cand, neighbor_window=2) is False


def test_expansion_distance_page_overlap_when_element_gap_exceeds_window() -> None:
    """Large on-page element distance falls through to the page-overlap branch."""
    s = _asset(source_file="f.pdf", start=0, end=0, page_number=1)
    c = _asset(source_file="f.pdf", start=10, end=10, page_number=1)
    d = expansion_distance(s, c, neighbor_window=2)
    # gap = 9 > neighbor_window → not returned early; same page → 2 + 1 + 9
    assert d == 12
