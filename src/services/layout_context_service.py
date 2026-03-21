"""
Layout-aware grouping of retrieved assets using existing metadata only.

Partitions the reranked asset list into ordered groups (same document flow) so the
prompt can surface page/section boundaries and nearby elements without a layout model.
"""

from __future__ import annotations

_MAX_ELEMENT_GAP = 5


def _norm_str(value: object | None) -> str | None:
    if value is None:
        return None
    s = str(value).strip()
    return s or None


def _meta(asset: dict) -> dict:
    return asset.get("metadata") or {}


def _source_file(asset: dict) -> str:
    m = _meta(asset)
    return _norm_str(asset.get("source_file")) or _norm_str(m.get("source_file")) or ""


def _page_bucket(asset: dict) -> int | None:
    """Single page label for grouping; None if unknown."""
    m = _meta(asset)
    pn = m.get("page_number")
    if pn is not None:
        try:
            return int(pn)
        except (TypeError, ValueError):
            pass
    ps, pe = m.get("page_start"), m.get("page_end")
    if ps is not None:
        try:
            a = int(ps)
            if pe is not None:
                b = int(pe)
                return (a + b) // 2
            return a
        except (TypeError, ValueError):
            pass
    return None


def _section_key(asset: dict) -> str:
    m = _meta(asset)
    for key in ("chunk_title", "section_title", "section_id"):
        s = _norm_str(m.get(key))
        if s:
            return s
    return ""


def _element_span_for_proximity(asset: dict) -> tuple[int, int] | None:
    m = _meta(asset)
    raw_s, raw_e = m.get("start_element_index"), m.get("end_element_index")
    if raw_s is not None and raw_e is not None:
        try:
            s, e = int(raw_s), int(raw_e)
        except (TypeError, ValueError):
            pass
        else:
            lo, hi = (s, e) if s <= e else (e, s)
            return lo, hi
    if asset.get("content_type") == "image":
        ii = m.get("image_index")
        if ii is not None:
            try:
                i = int(ii)
            except (TypeError, ValueError):
                return None
            return i, i
    return None


def describe_layout_group(group: list[dict]) -> str:
    """Short heading for a layout group (prompt-sized)."""
    if not group:
        return "Document context"
    first = group[0]
    sf = _source_file(first) or "unknown"
    pages: list[int] = []
    for a in group:
        p = _page_bucket(a)
        if p is not None:
            pages.append(p)
    page_part = ""
    if pages:
        lo, hi = min(pages), max(pages)
        page_part = f"Page {lo}" if lo == hi else f"Pages {lo}-{hi}"
    sec = _section_key(first)
    bits: list[str] = []
    if page_part:
        bits.append(page_part)
    if sec:
        bits.append(f"Section: {sec}")
    bits.append(sf)
    return " — ".join(bits) if bits else sf


def _element_gap(prev: tuple[int, int] | None, curr: tuple[int, int] | None) -> int | None:
    if not prev or not curr:
        return None
    alo, ahi = prev
    blo, bhi = curr
    if alo <= bhi and blo <= ahi:
        return 0
    if ahi < blo:
        return blo - ahi - 1
    if bhi < alo:
        return alo - bhi - 1
    return 0


class LayoutContextService:
    """
    Groups assets that share layout signals (file, page, section) and are element-nearby,
    preserving global rerank order within each group.
    """

    def group_assets(self, assets: list[dict]) -> list[list[dict]]:
        if not assets:
            return []
        if len(assets) == 1:
            return [list(assets)]

        groups: list[list[dict]] = []
        current: list[dict] = [assets[0]]
        first = assets[0]
        first_page = _page_bucket(first)
        prev_key = (
            _source_file(first),
            first_page if first_page is not None else "__page_unknown__",
            _section_key(first),
        )
        prev_span = _element_span_for_proximity(first)

        for asset in assets[1:]:
            sf = _source_file(asset)
            page = _page_bucket(asset)
            page_token: int | str = page if page is not None else "__page_unknown__"
            sec = _section_key(asset)
            key = (sf, page_token, sec)
            span = _element_span_for_proximity(asset)

            start_new = key != prev_key
            if not start_new and prev_span is not None and span is not None:
                gap = _element_gap(prev_span, span)
                if gap is not None and gap > _MAX_ELEMENT_GAP:
                    start_new = True

            if start_new:
                groups.append(current)
                current = [asset]
                prev_span = _element_span_for_proximity(asset)
            else:
                current.append(asset)
                prev_span = span if span is not None else None

            prev_key = key

        groups.append(current)
        return groups

    def validate_groups(self, assets: list[dict], groups: list[list[dict]]) -> bool:
        if not groups:
            return False
        flat: list[dict] = []
        for g in groups:
            flat.extend(g)
        if len(flat) != len(assets):
            return False
        return all(a is b for a, b in zip(assets, flat, strict=True))
