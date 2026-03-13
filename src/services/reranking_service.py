import re


DEFAULT_RERANKER_MODEL = "cross-encoder/ms-marco-MiniLM-L-6-v2"
MAX_TEXT_PREVIEW_CHARS = 1500
MAX_TABLE_TEXT_PREVIEW_CHARS = 1200


class RerankingService:
    """
    Asset-level reranking service.

    Stage 1:
    - FAISS retrieves a larger recall set from summary embeddings

    Stage 2:
    - this service reranks the rehydrated raw assets using a stricter relevance model

    Primary strategy:
    - sentence-transformers CrossEncoder

    Fallback strategy:
    - simple lexical overlap scoring when the cross-encoder is unavailable
    """

    def __init__(self, model_name: str = DEFAULT_RERANKER_MODEL):
        self.model_name = model_name
        self._model = None
        self._model_load_failed = False

    def rerank(self, query: str, raw_assets: list[dict], top_k: int) -> list[dict]:
        if not query or not raw_assets or top_k <= 0:
            return []

        candidates = [
            {
                "asset": asset,
                "candidate_text": self._build_candidate_text(asset),
            }
            for asset in raw_assets
        ]

        scores = self._score_candidates(query, candidates)

        ranked_items = sorted(
            zip(candidates, scores),
            key=lambda item: item[1],
            reverse=True,
        )

        selected_assets: list[dict] = []

        for candidate, score in ranked_items[:top_k]:
            asset = candidate["asset"]
            asset_copy = {
                **asset,
                "metadata": {
                    **(asset.get("metadata", {}) or {}),
                    "rerank_score": float(score),
                },
            }
            selected_assets.append(asset_copy)

        return selected_assets

    def _score_candidates(self, query: str, candidates: list[dict]) -> list[float]:
        model = self._get_model()

        if model is not None:
            try:
                pairs = [(query, candidate["candidate_text"]) for candidate in candidates]
                raw_scores = model.predict(pairs)
                return [float(score) for score in raw_scores]
            except Exception:
                pass

        return [self._fallback_score(query, candidate["candidate_text"]) for candidate in candidates]

    def _get_model(self):
        if self._model_load_failed:
            return None

        if self._model is not None:
            return self._model

        try:
            from sentence_transformers import CrossEncoder

            self._model = CrossEncoder(self.model_name)
            return self._model
        except Exception:
            self._model_load_failed = True
            return None

    def _build_candidate_text(self, asset: dict) -> str:
        content_type = asset.get("content_type", "unknown")
        source_file = asset.get("source_file", "unknown")
        summary = (asset.get("summary", "") or "").strip()
        raw_content = (asset.get("raw_content", "") or "").strip()
        metadata = asset.get("metadata", {}) or {}

        page_number = metadata.get("page_number")
        page_start = metadata.get("page_start")
        page_end = metadata.get("page_end")
        table_title = metadata.get("table_title")
        table_text = (metadata.get("table_text") or "").strip()
        image_title = metadata.get("image_title")
        start_element_index = metadata.get("start_element_index")
        end_element_index = metadata.get("end_element_index")

        locator_parts = [f"content_type: {content_type}", f"source_file: {source_file}"]

        if page_number is not None:
            locator_parts.append(f"page: {page_number}")
        elif page_start is not None and page_end is not None:
            locator_parts.append(f"pages: {page_start}-{page_end}")
        elif page_start is not None:
            locator_parts.append(f"page: {page_start}")

        if start_element_index is not None and end_element_index is not None:
            locator_parts.append(f"elements: {start_element_index}-{end_element_index}")

        if table_title:
            locator_parts.append(f"table_title: {table_title}")

        if image_title:
            locator_parts.append(f"image_title: {image_title}")

        blocks = [
            " | ".join(locator_parts),
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

    def _fallback_score(self, query: str, candidate_text: str) -> float:
        query_tokens = self._tokenize(query)
        candidate_tokens = self._tokenize(candidate_text)

        if not query_tokens or not candidate_tokens:
            return 0.0

        overlap = len(query_tokens.intersection(candidate_tokens))
        query_coverage = overlap / max(len(query_tokens), 1)

        phrase_bonus = 0.0
        normalized_query = query.lower().strip()
        normalized_candidate = candidate_text.lower()

        if normalized_query and normalized_query in normalized_candidate:
            phrase_bonus = 0.25

        return float(query_coverage + phrase_bonus)

    def _tokenize(self, text: str) -> set[str]:
        return {
            token
            for token in re.findall(r"[a-zA-Z0-9_/-]+", text.lower())
            if len(token) > 1
        }
