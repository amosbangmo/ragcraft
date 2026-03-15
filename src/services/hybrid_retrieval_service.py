import re

from langchain_core.documents import Document
from rank_bm25 import BM25Okapi


MAX_TEXT_PREVIEW_CHARS = 1200
MAX_TABLE_TEXT_PREVIEW_CHARS = 1000


class HybridRetrievalService:
    """
    Lightweight lexical retrieval layer over stored asset summaries.

    Source of truth:
    - SQLite raw assets / summaries already stored in the docstore

    Output:
    - LangChain Documents compatible with the existing RAG pipeline

    Notes:
    - this is query-time BM25, not a persisted lexical index
    - intended as a complementary recall channel to FAISS
    """

    def lexical_search(
        self,
        *,
        query: str,
        assets: list[dict],
        k: int,
    ) -> list[Document]:
        normalized_query = (query or "").strip()
        if not normalized_query or not assets or k <= 0:
            return []

        prepared_candidates: list[dict] = []
        corpus_tokens: list[list[str]] = []

        for asset in assets:
            candidate_text = self._build_candidate_text(asset)
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

        bm25 = BM25Okapi(corpus_tokens)
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

            summary = (asset.get("summary", "") or "").strip()
            fallback_text = candidate["candidate_text"][:1500]

            documents.append(
                Document(
                    page_content=summary or fallback_text,
                    metadata=metadata,
                )
            )

        return documents

    def _build_candidate_text(self, asset: dict) -> str:
        content_type = asset.get("content_type", "unknown")
        source_file = asset.get("source_file", "unknown")
        summary = (asset.get("summary", "") or "").strip()
        raw_content = (asset.get("raw_content", "") or "").strip()
        metadata = asset.get("metadata", {}) or {}

        table_title = metadata.get("table_title")
        table_text = (metadata.get("table_text") or "").strip()
        image_title = metadata.get("image_title")
        chunk_title = metadata.get("chunk_title")
        page_number = metadata.get("page_number")
        page_start = metadata.get("page_start")
        page_end = metadata.get("page_end")

        header_parts = [
            f"source_file: {source_file}",
            f"content_type: {content_type}",
        ]

        if chunk_title:
            header_parts.append(f"chunk_title: {chunk_title}")
        if table_title:
            header_parts.append(f"table_title: {table_title}")
        if image_title:
            header_parts.append(f"image_title: {image_title}")

        if page_number is not None:
            header_parts.append(f"page: {page_number}")
        elif page_start is not None and page_end is not None:
            header_parts.append(f"pages: {page_start}-{page_end}")
        elif page_start is not None:
            header_parts.append(f"page: {page_start}")

        blocks = [
            " | ".join(header_parts),
            f"summary: {summary}",
        ]

        if content_type == "text":
            blocks.append(f"raw_text_excerpt: {raw_content[:MAX_TEXT_PREVIEW_CHARS]}")
        elif content_type == "table":
            blocks.append(f"table_text_excerpt: {table_text[:MAX_TABLE_TEXT_PREVIEW_CHARS]}")
            blocks.append(f"table_html_excerpt: {raw_content[:800]}")
        elif content_type == "image":
            blocks.append(f"image_summary: {summary}")
        else:
            blocks.append(f"raw_excerpt: {raw_content[:1000]}")

        return "\n".join(block for block in blocks if block.strip())

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
