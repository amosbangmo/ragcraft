import re

from langchain_core.documents import Document
from rank_bm25 import BM25Okapi

from src.domain.retrieval_filters import RetrievalFilters, filter_raw_assets_by_filters


class HybridRetrievalService:
    """
    Lightweight lexical retrieval layer over stored assets.

    BM25 is run only on: ``raw_content``, ``metadata.table_title``,
    and ``metadata.image_title`` (no summary, filenames, or other metadata).

    Source of truth:
    - SQLite raw assets already stored in the docstore

    Output:
    - LangChain Documents compatible with the existing RAG pipeline

    Notes:
    - this is query-time BM25, not a persisted lexical index
    - intended as a complementary recall channel to FAISS
    """

    def __init__(
        self,
        *,
        k1: float = 1.5,
        b: float = 0.75,
        epsilon: float = 0.25,
    ) -> None:
        self._bm25_k1 = k1
        self._bm25_b = b
        self._bm25_epsilon = epsilon

    def lexical_search(
        self,
        *,
        query: str,
        assets: list[dict],
        k: int,
        filters: RetrievalFilters | None = None,
    ) -> list[Document]:
        normalized_query = (query or "").strip()
        if not normalized_query or not assets or k <= 0:
            return []

        scoped_assets = filter_raw_assets_by_filters(assets, filters)
        if not scoped_assets:
            return []

        prepared_candidates: list[dict] = []
        corpus_tokens: list[list[str]] = []

        for asset in scoped_assets:
            candidate_text = self._build_lexical_candidate_text(asset)
            tokens = self._tokenize(candidate_text)

            if not tokens:
                continue

            prepared_candidates.append(
                {
                    "asset": asset,
                    "candidate_text": candidate_text,
                }
            )
            corpus_tokens.append(tokens)

        if not prepared_candidates:
            return []

        query_tokens = self._tokenize(normalized_query)
        if not query_tokens:
            return []

        bm25 = BM25Okapi(
            corpus_tokens,
            k1=self._bm25_k1,
            b=self._bm25_b,
            epsilon=self._bm25_epsilon,
        )
        raw_scores = list(bm25.get_scores(query_tokens))

        if not raw_scores:
            return []

        normalized_scores = self._normalize_scores(raw_scores)

        ranked_items = sorted(
            zip(prepared_candidates, normalized_scores),
            key=lambda item: item[1],
            reverse=True,
        )

        documents: list[Document] = []

        for candidate, normalized_score in ranked_items[:k]:
            asset = candidate["asset"]
            metadata = {
                **(asset.get("metadata", {}) or {}),
                "retrieval_score": float(normalized_score),
                "retrieval_mode": "bm25",
            }
            doc_id = asset.get("doc_id")
            if doc_id:
                metadata.setdefault("doc_id", doc_id)
            source_file = asset.get("source_file")
            if source_file:
                metadata.setdefault("source_file", source_file)
            content_type = asset.get("content_type")
            if content_type:
                metadata.setdefault("content_type", content_type)

            summary = (asset.get("summary", "") or "").strip()
            fallback_text = candidate["candidate_text"][:1500]

            documents.append(
                Document(
                    page_content=summary or fallback_text,
                    metadata=metadata,
                )
            )

        return documents

    def _build_lexical_candidate_text(self, asset: dict) -> str:
        """
        Corpus text for BM25: only ``raw_content``, ``table_title``, ``image_title``.
        """
        metadata = asset.get("metadata", {}) or {}
        parts: list[str] = []

        raw_content = (asset.get("raw_content", "") or "").strip()
        if raw_content:
            parts.append(raw_content)

        for key in ("table_title", "image_title"):
            value = metadata.get(key)
            if value is None:
                continue
            s = str(value).strip()
            if s:
                parts.append(s)

        return "\n".join(parts)

    def _tokenize(self, text: str) -> list[str]:
        return [
            token
            for token in re.findall(r"[a-zA-Z0-9_/-]+", text.lower())
            if len(token) > 1
        ]

    def _normalize_scores(self, raw_scores: list[float]) -> list[float]:
        if not raw_scores:
            return []

        max_score = max(raw_scores)
        min_score = min(raw_scores)

        if max_score == min_score:
            if max_score <= 0:
                return [0.0 for _ in raw_scores]
            return [1.0 for _ in raw_scores]

        return [
            float((score - min_score) / (max_score - min_score))
            for score in raw_scores
        ]
