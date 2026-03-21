"""
Section-aware retrieval expansion: widen the rerank pool with same-section and
neighbor chunks so related context is scored together.
"""

from __future__ import annotations

from dataclasses import dataclass


def _norm_str(value: object | None) -> str | None:
    if value is None:
        return None
    s = str(value).strip()
    return s or None


def _meta(asset: dict) -> dict:
    return asset.get("metadata") or {}


def _source_file(asset: dict) -> str | None:
    return _norm_str(asset.get("source_file")) or _norm_str(_meta(asset).get("source_file"))


def _element_span(asset: dict) -> tuple[int, int] | None:
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


def _page_span(asset: dict) -> tuple[int, int] | None:
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


def _pages_overlap(a: tuple[int, int] | None, b: tuple[int, int] | None) -> bool:
    if not a or not b:
        return False
    return not (a[1] < b[0] or b[1] < a[0])


def _element_gap(
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


def _has_expansion_signals(asset: dict) -> bool:
    m = _meta(asset)
    if _norm_str(m.get("section_id")):
        return True
    if _norm_str(m.get("chunk_title")):
        return True
    if _norm_str(m.get("section_title")):
        return True
    if _element_span(asset) is not None:
        return True
    if _page_span(asset) is not None:
        return True
    return False


def _anchor_cap_key(seed: dict) -> str:
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
    if _element_span(seed) is not None or _page_span(seed) is not None:
        return f"prox:{sf}"
    return f"none:{sf}"


def _distance(seed: dict, candidate: dict, *, neighbor_window: int) -> int:
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

    es, ec = _element_span(seed), _element_span(candidate)
    gap = _element_gap(es, ec)
    if gap is not None and gap <= neighbor_window:
        return gap

    ps, pc = _page_span(seed), _page_span(candidate)
    if _pages_overlap(ps, pc):
        if gap is not None:
            return neighbor_window + 1 + gap
        return neighbor_window + 1

    return 10**9


def _eligible_pair(
    seed: dict,
    candidate: dict,
    *,
    neighbor_window: int,
) -> bool:
    if not _has_expansion_signals(seed):
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

    es, ec = _element_span(seed), _element_span(candidate)
    gap = _element_gap(es, ec)
    if gap is not None and gap <= neighbor_window:
        return True

    ps, pc = _page_span(seed), _page_span(candidate)
    if _pages_overlap(ps, pc):
        return True

    return False


@dataclass(frozen=True)
class SectionExpansionResult:
    assets: list[dict]
    applied: bool
    section_expansion_count: int
    expanded_assets_count: int


class SectionRetrievalService:
    def expand(
        self,
        *,
        config: object,
        retrieved_assets: list[dict],
        all_assets: list[dict],
    ) -> SectionExpansionResult:
        if not getattr(config, "enable_section_expansion", False):
            return SectionExpansionResult(
                assets=list(retrieved_assets),
                applied=False,
                section_expansion_count=0,
                expanded_assets_count=len(retrieved_assets),
            )

        if not retrieved_assets:
            return SectionExpansionResult(
                assets=[],
                applied=False,
                section_expansion_count=0,
                expanded_assets_count=0,
            )

        if not all_assets:
            return SectionExpansionResult(
                assets=list(retrieved_assets),
                applied=False,
                section_expansion_count=0,
                expanded_assets_count=len(retrieved_assets),
            )

        if not any(_has_expansion_signals(a) for a in retrieved_assets):
            return SectionExpansionResult(
                assets=list(retrieved_assets),
                applied=False,
                section_expansion_count=0,
                expanded_assets_count=len(retrieved_assets),
            )

        neighbor_window = max(0, int(getattr(config, "section_expansion_neighbor_window", 2)))
        max_per_section = max(1, int(getattr(config, "section_expansion_max_per_section", 12)))
        global_max = max(len(retrieved_assets), int(getattr(config, "section_expansion_global_max", 64)))

        by_id: dict[str, dict] = {}
        for a in all_assets:
            did = a.get("doc_id")
            if did and did not in by_id:
                by_id[str(did)] = a

        pool: list[dict] = []
        pool_ids: set[str] = set()
        for a in retrieved_assets:
            did = a.get("doc_id")
            if not did or did in pool_ids:
                continue
            if did not in by_id:
                pool.append(a)
            else:
                pool.append(by_id[str(did)])
            pool_ids.add(str(did))

        key_counts: dict[str, int] = {}
        for a in pool:
            k = _anchor_cap_key(a)
            key_counts[k] = key_counts.get(k, 0) + 1

        seeds_by_id: dict[str, dict] = {
            str(s["doc_id"]): s for s in pool if s.get("doc_id")
        }

        pair_scores: list[tuple[int, str, str, dict]] = []
        for seed in pool:
            sid = seed.get("doc_id")
            if not sid:
                continue
            for cand in by_id.values():
                cid = cand.get("doc_id")
                if not cid or str(cid) in pool_ids:
                    continue
                if not _eligible_pair(seed, cand, neighbor_window=neighbor_window):
                    continue
                dist = _distance(seed, cand, neighbor_window=neighbor_window)
                pair_scores.append((dist, str(sid), str(cid), cand))

        pair_scores.sort(key=lambda t: (t[0], t[1], t[2]))

        added = 0
        for dist, seed_id, cid, cand in pair_scores:
            if len(pool) >= global_max:
                break
            if str(cid) in pool_ids:
                continue
            seed = seeds_by_id.get(seed_id)
            if seed is None:
                continue
            cap_key = _anchor_cap_key(seed)
            if key_counts.get(cap_key, 0) >= max_per_section:
                continue
            if dist >= 10**9:
                continue

            pool.append(cand)
            pool_ids.add(str(cid))
            key_counts[cap_key] = key_counts.get(cap_key, 0) + 1
            added += 1

        applied = added > 0
        return SectionExpansionResult(
            assets=pool,
            applied=applied,
            section_expansion_count=added,
            expanded_assets_count=len(pool),
        )
