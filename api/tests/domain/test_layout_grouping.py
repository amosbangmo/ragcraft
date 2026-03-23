"""Tests for :mod:`domain.rag.retrieval.layout_grouping`."""

from __future__ import annotations

from domain.rag.retrieval.layout_grouping import (
    describe_layout_group,
    group_assets_by_layout,
    validate_layout_groups,
)


def _a(
    *,
    sf: str = "doc.pdf",
    page_number: int | None = None,
    page_start: int | None = None,
    page_end: int | None = None,
    section: str | None = None,
    start_el: int | None = None,
    end_el: int | None = None,
    content_type: str | None = None,
    image_index: int | None = None,
) -> dict:
    meta: dict = {}
    if page_number is not None:
        meta["page_number"] = page_number
    if page_start is not None:
        meta["page_start"] = page_start
    if page_end is not None:
        meta["page_end"] = page_end
    if section is not None:
        meta["section_id"] = section
    if start_el is not None and end_el is not None:
        meta["start_element_index"] = start_el
        meta["end_element_index"] = end_el
    if image_index is not None:
        meta["image_index"] = image_index
    out: dict = {"source_file": sf, "metadata": meta}
    if content_type is not None:
        out["content_type"] = content_type
    return out


def test_describe_layout_group_empty() -> None:
    assert describe_layout_group([]) == "Document context"


def test_describe_layout_group_single_page() -> None:
    g = [_a(page_number=2, section="Intro")]
    title = describe_layout_group(g)
    assert "Page 2" in title
    assert "Intro" in title


def test_describe_layout_group_page_range() -> None:
    g = [_a(page_number=1), _a(page_number=3)]
    assert "Pages 1-3" in describe_layout_group(g)


def test_page_bucket_invalid_page_number_falls_through() -> None:
    a = _a()
    a["metadata"]["page_number"] = "nope"
    a["metadata"]["page_start"] = 2
    a["metadata"]["page_end"] = 4
    groups = group_assets_by_layout([a])
    assert len(groups) == 1


def test_group_splits_on_large_element_gap() -> None:
    a1 = _a(sf="d.pdf", section="s", start_el=0, end_el=0)
    a2 = _a(sf="d.pdf", section="s", start_el=20, end_el=20)
    groups = group_assets_by_layout([a1, a2])
    assert len(groups) == 2


def test_image_element_span_from_index() -> None:
    img = _a(sf="d.pdf", section="s", content_type="image", image_index=5)
    img2 = _a(sf="d.pdf", section="s", content_type="image", image_index=6)
    groups = group_assets_by_layout([img, img2])
    assert len(groups) == 1


def test_validate_layout_groups() -> None:
    assets = [_a(page_number=1), _a(page_number=1)]
    groups = group_assets_by_layout(assets)
    assert validate_layout_groups(assets, groups) is True
    assert validate_layout_groups(assets, []) is False
