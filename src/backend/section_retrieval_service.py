"""
Section-aware retrieval expansion: widen the rerank pool with same-section and
neighbor chunks so related context is scored together.

Pure eligibility/distance rules: :mod:`src.domain.retrieval.section_expansion_rules`.
"""

from __future__ import annotations

from dataclasses import dataclass

from src.domain.retrieval.section_expansion_rules import (
    anchor_cap_key,
    eligible_expansion_pair,
    expansion_distance,
    has_expansion_signals,
)


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

        if not any(has_expansion_signals(a) for a in retrieved_assets):
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
            k = anchor_cap_key(a)
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
                if not eligible_expansion_pair(seed, cand, neighbor_window=neighbor_window):
                    continue
                dist = expansion_distance(seed, cand, neighbor_window=neighbor_window)
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
            cap_key = anchor_cap_key(seed)
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
