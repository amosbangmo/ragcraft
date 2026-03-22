"""
Weighted Reciprocal Rank Fusion (RRF) over two ranked summary document lists.

Domain policy used after parallel semantic (FAISS) and lexical (BM25) recall paths merge.
"""

from __future__ import annotations

from src.domain.retrieval_settings import RetrievalSettings
from src.domain.summary_recall_document import SummaryRecallDocument


def merge_summary_documents_weighted_rrf(
    *,
    settings: RetrievalSettings,
    primary_docs: list[SummaryRecallDocument],
    secondary_docs: list[SummaryRecallDocument],
    max_docs: int | None = None,
) -> list[SummaryRecallDocument]:
    """
    Merge two ranked document lists using weighted RRF.

    Final score for each doc_id:
      beta * (1 / (rrf_k + rank_semantic)) + (1 - beta) * (1 / (rrf_k + rank_lexical))
    for each list where the doc appears (primary = semantic/FAISS, secondary = BM25).
    """
    rrf_k = settings.rrf_k
    hybrid_beta = settings.hybrid_beta

    primary_ranks: dict[str, int] = {}
    secondary_ranks: dict[str, int] = {}
    docs_by_id: dict[str, SummaryRecallDocument] = {}
    first_seen_order: dict[str, int] = {}

    def _ingest(docs: list[SummaryRecallDocument], *, target_ranks: dict[str, int]) -> None:
        for rank, doc in enumerate(docs, start=1):
            doc_id = doc.metadata.get("doc_id")
            if not doc_id:
                continue

            target_ranks.setdefault(doc_id, rank)

            if doc_id not in docs_by_id:
                docs_by_id[doc_id] = doc
                first_seen_order[doc_id] = len(first_seen_order)

    _ingest(primary_docs, target_ranks=primary_ranks)
    _ingest(secondary_docs, target_ranks=secondary_ranks)

    fused: list[tuple[str, float, int, int]] = []
    all_doc_ids = set(docs_by_id.keys())

    for doc_id in all_doc_ids:
        score = 0.0
        min_rank = 10**18

        if doc_id in primary_ranks:
            rank = primary_ranks[doc_id]
            score += hybrid_beta * (1.0 / (rrf_k + rank))
            min_rank = min(min_rank, rank)

        if doc_id in secondary_ranks:
            rank = secondary_ranks[doc_id]
            score += (1.0 - hybrid_beta) * (1.0 / (rrf_k + rank))
            min_rank = min(min_rank, rank)

        fused.append((doc_id, score, min_rank, first_seen_order[doc_id]))

    fused.sort(key=lambda item: (-item[1], item[2], item[3]))

    limit = max_docs if max_docs is not None else len(fused)
    fused_doc_ids = [doc_id for doc_id, _, _, _ in fused[:limit]]
    return [docs_by_id[doc_id] for doc_id in fused_doc_ids]
