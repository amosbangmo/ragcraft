"""Pure rules for section-aware retrieval expansion (pair eligibility, distance, caps)."""

from __future__ import annotations


def _norm_str(value: object | None) -> str | None:
    if value is None:
        return None
    s = str(value).strip()
    return s or None


def _meta(asset: dict) -> dict:
    return asset.get("metadata") or {}


def _source_file(asset: dict) -> str | None:
    return _norm_str(asset.get("source_file")) or _norm_str(_meta(asset).get("source_file"))


def element_span(asset: dict) -> tuple[int, int] | None:
    m = _meta(asset)
    raw_s, raw_e = m.get("start_element_index"), m.get("end_element_index")
    if raw_s is None or raw_e is None:
        return None
    try:
        s, e = int(raw_s), int(raw_e)
    except (TypeError, ValueError):
        return None
    lo, hi = (s, e) if s <= e else (e, s)
    return lo, hi


def page_span(asset: dict) -> tuple[int, int] | None:
    m = _meta(asset)
    ps, pe = m.get("page_start"), m.get("page_end")
    if ps is not None and pe is not None:
        try:
            a, b = int(ps), int(pe)
        except (TypeError, ValueError):
            return None
        lo, hi = (a, b) if a <= b else (b, a)
        return lo, hi
    pn = m.get("page_number")
    if pn is not None:
        try:
            p = int(pn)
        except (TypeError, ValueError):
            return None
        return p, p
    return None


def pages_overlap(a: tuple[int, int] | None, b: tuple[int, int] | None) -> bool:
    if not a or not b:
        return False
    return not (a[1] < b[0] or b[1] < a[0])


def element_gap(
    span_a: tuple[int, int] | None,
    span_b: tuple[int, int] | None,
) -> int | None:
    if not span_a or not span_b:
        return None
    alo, ahi = span_a
    blo, bhi = span_b
    if alo <= bhi and blo <= ahi:
        return 0
    if ahi < blo:
        return blo - ahi - 1
    if bhi < alo:
        return alo - bhi - 1
    return 0


def has_expansion_signals(asset: dict) -> bool:
    m = _meta(asset)
    if _norm_str(m.get("section_id")):
        return True
    if _norm_str(m.get("chunk_title")):
        return True
    if _norm_str(m.get("section_title")):
        return True
    if element_span(asset) is not None:
        return True
    if page_span(asset) is not None:
        return True
    return False


def anchor_cap_key(seed: dict) -> str:
    """Bucket for per-section expansion limits (anchored on the retrieved seed)."""
    m = _meta(seed)
    sf = _source_file(seed) or ""
    sid = _norm_str(m.get("section_id"))
    if sid:
        return f"sid:{sf}:{sid}"
    ct = _norm_str(m.get("chunk_title"))
    if ct:
        return f"ct:{sf}:{ct}"
    st = _norm_str(m.get("section_title"))
    if st:
        return f"st:{sf}:{st}"
    if element_span(seed) is not None or page_span(seed) is not None:
        return f"prox:{sf}"
    return f"none:{sf}"


def expansion_distance(seed: dict, candidate: dict, *, neighbor_window: int) -> int:
    ms, mc = _meta(seed), _meta(candidate)

    sid_s = _norm_str(ms.get("section_id"))
    sid_c = _norm_str(mc.get("section_id"))
    if sid_s and sid_c and sid_s == sid_c:
        return 0

    ct_s = _norm_str(ms.get("chunk_title"))
    ct_c = _norm_str(mc.get("chunk_title"))
    if ct_s and ct_c and ct_s == ct_c:
        return 0

    st_s = _norm_str(ms.get("section_title"))
    st_c = _norm_str(mc.get("section_title"))
    if st_s and st_c and st_s == st_c:
        return 0

    es, ec = element_span(seed), element_span(candidate)
    gap = element_gap(es, ec)
    if gap is not None and gap <= neighbor_window:
        return gap

    ps, pc = page_span(seed), page_span(candidate)
    if pages_overlap(ps, pc):
        if gap is not None:
            return neighbor_window + 1 + gap
        return neighbor_window + 1

    return 10**9


def eligible_expansion_pair(
    seed: dict,
    candidate: dict,
    *,
    neighbor_window: int,
) -> bool:
    if not has_expansion_signals(seed):
        return False

    sf_s = _source_file(seed)
    sf_c = _source_file(candidate)
    if not sf_s or sf_s != sf_c:
        return False

    ms, mc = _meta(seed), _meta(candidate)

    sid_s = _norm_str(ms.get("section_id"))
    sid_c = _norm_str(mc.get("section_id"))
    if sid_s and sid_c and sid_s == sid_c:
        return True

    ct_s = _norm_str(ms.get("chunk_title"))
    ct_c = _norm_str(mc.get("chunk_title"))
    if ct_s and ct_c and ct_s == ct_c:
        return True

    st_s = _norm_str(ms.get("section_title"))
    st_c = _norm_str(mc.get("section_title"))
    if st_s and st_c and st_s == st_c:
        return True

    es, ec = element_span(seed), element_span(candidate)
    gap = element_gap(es, ec)
    if gap is not None and gap <= neighbor_window:
        return True

    ps, pc = page_span(seed), page_span(candidate)
    if pages_overlap(ps, pc):
        return True

    return False
