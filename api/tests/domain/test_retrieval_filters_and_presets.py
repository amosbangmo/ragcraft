"""Tests for retrieval filters and preset parsing."""

from __future__ import annotations

from domain.rag.retrieval_filters import (
    RetrievalFilters,
    filter_raw_assets_by_filters,
    raw_asset_matches_filters,
    summary_document_matches_filters,
    vector_search_fetch_k,
)
from domain.rag.retrieval_presets import (
    RetrievalPreset,
    parse_retrieval_preset,
)
from domain.rag.summary_recall_document import SummaryRecallDocument


def test_retrieval_filters_empty() -> None:
    f = RetrievalFilters()
    assert f.is_empty() is True
    assert f.to_dict()["page_start"] is None


def test_raw_asset_matches_source_files() -> None:
    filters = RetrievalFilters(source_files=["a.pdf"])
    asset = {"source_file": "a.pdf", "metadata": {}}
    assert raw_asset_matches_filters(asset, filters) is True
    assert raw_asset_matches_filters({"source_file": "b.pdf", "metadata": {}}, filters) is False


def test_raw_asset_normalize_none_in_str_list() -> None:
    filters = RetrievalFilters(source_files=["ok", "  "])
    asset = {"source_file": "ok", "metadata": {}}
    assert raw_asset_matches_filters(asset, filters) is True


def test_raw_asset_page_numbers_require_span() -> None:
    filters = RetrievalFilters(page_numbers=[1])
    no_page = {"source_file": "x", "metadata": {}}
    assert raw_asset_matches_filters(no_page, filters) is False


def test_raw_asset_page_start_end_partial_noop_branch() -> None:
    """Only both page_start and page_end together constrain the asset."""
    filters = RetrievalFilters(page_start=1)
    asset = {"source_file": "x", "metadata": {"page_number": 1}}
    assert raw_asset_matches_filters(asset, filters) is True


def test_filter_raw_assets_none_or_empty() -> None:
    assets = [{"source_file": "a", "metadata": {}}]
    assert filter_raw_assets_by_filters(assets, None) == assets
    assert filter_raw_assets_by_filters(assets, RetrievalFilters()) == assets


def test_summary_document_matches_filters_file_name_fallback() -> None:
    doc = SummaryRecallDocument(
        page_content="t",
        metadata={"file_name": "z.pdf", "content_type": "text/plain"},
    )
    filters = RetrievalFilters(source_files=["z.pdf"])
    assert summary_document_matches_filters(doc, filters) is True


def test_vector_search_fetch_k() -> None:
    assert vector_search_fetch_k(base_k=5, filters=None) == 5
    assert vector_search_fetch_k(base_k=5, filters=RetrievalFilters(source_files=["a"])) >= 25


def test_parse_retrieval_preset_variants() -> None:
    assert parse_retrieval_preset(None) is RetrievalPreset.BALANCED
    assert parse_retrieval_preset("  ") is RetrievalPreset.BALANCED
    assert parse_retrieval_preset(RetrievalPreset.PRECISE) is RetrievalPreset.PRECISE
    assert parse_retrieval_preset("precise") is RetrievalPreset.PRECISE
    assert parse_retrieval_preset("PRECISE") is RetrievalPreset.PRECISE
    assert parse_retrieval_preset("Precise") is RetrievalPreset.PRECISE
    assert parse_retrieval_preset("unknown-mode-xyz") is RetrievalPreset.BALANCED
