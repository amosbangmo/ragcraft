from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from src.domain.summary_recall_document import SummaryRecallDocument


@dataclass(frozen=True)
class RetrievalFilters:
    source_files: list[str] = field(default_factory=list)
    content_types: list[str] = field(default_factory=list)
    page_numbers: list[int] = field(default_factory=list)
    page_start: int | None = None
    page_end: int | None = None

    def is_empty(self) -> bool:
        return (
            not self.source_files
            and not self.content_types
            and not self.page_numbers
            and self.page_start is None
            and self.page_end is None
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "source_files": list(self.source_files),
            "content_types": list(self.content_types),
            "page_numbers": list(self.page_numbers),
            "page_start": self.page_start,
            "page_end": self.page_end,
        }


def _normalize_str_list(values: list[str] | None) -> list[str]:
    if not values:
        return []
    out: list[str] = []
    for v in values:
        if v is None:
            continue
        s = str(v).strip()
        if s:
            out.append(s)
    return out


def _normalize_int_list(values: list[int] | None) -> list[int]:
    if not values:
        return []
    out: list[int] = []
    for v in values:
        try:
            out.append(int(v))
        except (TypeError, ValueError):
            continue
    return out


def _parse_positive_int(value: Any) -> int | None:
    if value is None:
        return None
    try:
        n = int(value)
    except (TypeError, ValueError):
        return None
    if n <= 0:
        return None
    return n


def _asset_page_span(metadata: dict | None) -> tuple[int, int] | None:
    meta = metadata or {}
    pn = _parse_positive_int(meta.get("page_number"))
    if pn is not None:
        return (pn, pn)
    ps = _parse_positive_int(meta.get("page_start"))
    pe = _parse_positive_int(meta.get("page_end"))
    if ps is not None and pe is not None:
        if ps > pe:
            ps, pe = pe, ps
        return (ps, pe)
    return None


def _ranges_overlap(a0: int, a1: int, b0: int, b1: int) -> bool:
    return not (a1 < b0 or a0 > b1)


def raw_asset_matches_filters(asset: dict, filters: RetrievalFilters) -> bool:
    if filters.is_empty():
        return True

    meta = asset.get("metadata", {}) or {}

    wanted_files = _normalize_str_list(filters.source_files)
    if wanted_files:
        sf = (asset.get("source_file") or "").strip()
        if sf not in set(wanted_files):
            return False

    wanted_types = {t.lower() for t in _normalize_str_list(filters.content_types)}
    if wanted_types:
        ct = (asset.get("content_type") or "").strip().lower()
        if ct not in wanted_types:
            return False

    span = _asset_page_span(meta)
    pages = _normalize_int_list(filters.page_numbers)
    if pages:
        if span is None:
            return False
        a0, a1 = span
        if not any(_ranges_overlap(a0, a1, p, p) for p in pages):
            return False

    fs = _parse_positive_int(filters.page_start)
    fe = _parse_positive_int(filters.page_end)
    if fs is not None and fe is not None:
        if fs > fe:
            fs, fe = fe, fs
        if span is None:
            return False
        a0, a1 = span
        if not _ranges_overlap(a0, a1, fs, fe):
            return False
    elif fs is not None or fe is not None:
        pass

    return True


def _summary_source_file(metadata: dict | None) -> str:
    meta = metadata or {}
    for key in ("source_file", "file_name"):
        v = meta.get(key)
        if v is not None and str(v).strip():
            return str(v).strip()
    return ""


def summary_document_matches_filters(doc: SummaryRecallDocument, filters: RetrievalFilters) -> bool:
    if filters.is_empty():
        return True

    meta = doc.metadata or {}

    wanted_files = _normalize_str_list(filters.source_files)
    if wanted_files:
        sf = _summary_source_file(meta)
        if sf not in set(wanted_files):
            return False

    wanted_types = {t.lower() for t in _normalize_str_list(filters.content_types)}
    if wanted_types:
        ct = (meta.get("content_type") or "").strip().lower()
        if ct not in wanted_types:
            return False

    span = _asset_page_span(meta)
    pages = _normalize_int_list(filters.page_numbers)
    if pages:
        if span is None:
            return False
        a0, a1 = span
        if not any(_ranges_overlap(a0, a1, p, p) for p in pages):
            return False

    fs = _parse_positive_int(filters.page_start)
    fe = _parse_positive_int(filters.page_end)
    if fs is not None and fe is not None:
        if fs > fe:
            fs, fe = fe, fs
        if span is None:
            return False
        a0, a1 = span
        if not _ranges_overlap(a0, a1, fs, fe):
            return False

    return True


def filter_raw_assets_by_filters(assets: list[dict], filters: RetrievalFilters | None) -> list[dict]:
    if filters is None or filters.is_empty():
        return list(assets)
    return [a for a in assets if raw_asset_matches_filters(a, filters)]


def filter_summary_documents_by_filters(
    docs: list[SummaryRecallDocument],
    filters: RetrievalFilters | None,
) -> list[SummaryRecallDocument]:
    if filters is None or filters.is_empty():
        return list(docs)
    return [d for d in docs if summary_document_matches_filters(d, filters)]


def vector_search_fetch_k(*, base_k: int, filters: RetrievalFilters | None) -> int:
    if filters is None or filters.is_empty():
        return base_k
    return max(base_k * 4, base_k + 20)
