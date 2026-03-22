import re


DEFAULT_RERANKER_MODEL = "cross-encoder/ms-marco-MiniLM-L-6-v2"


class RerankingService:
    """
    Asset-level reranking service.

    Stage 1:
    - FAISS retrieves a larger recall set from summary embeddings

    Stage 2:
    - this service reranks the rehydrated raw assets using a stricter relevance model
      over candidate text built from raw_content plus metadata table_title and image_title

    Primary strategy:
    - sentence-transformers CrossEncoder

    Fallback strategy:
    - simple lexical overlap scoring when the cross-encoder is unavailable
    """

    def __init__(self, model_name: str = DEFAULT_RERANKER_MODEL):
        self.model_name = model_name
        self._model = None
        self._model_load_failed = False

    def rerank(
        self,
        query: str,
        raw_assets: list[dict],
        top_k: int,
        *,
        prefer_tables: bool = False,
        table_boost: float = 0.0,
    ) -> list[dict]:
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

        if prefer_tables and table_boost > 0:
            scores = [
                float(score)
                + (
                    float(table_boost)
                    if (candidate["asset"].get("content_type") == "table")
                    else 0.0
                )
                for score, candidate in zip(scores, candidates)
            ]

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
        metadata = asset.get("metadata", {}) or {}
        parts: list[str] = []

        raw_content = (asset.get("raw_content", "") or "").strip()
        if raw_content:
            parts.append(raw_content)

        table_title = metadata.get("table_title")
        if table_title is not None:
            s = str(table_title).strip()
            if s:
                parts.append(s)

        structured = metadata.get("structured_table") or {}
        headers = structured.get("headers") or []
        if headers:
            hdr_text = " ".join(str(h).strip() for h in headers if str(h).strip())
            if hdr_text:
                parts.append(hdr_text)

        image_title = metadata.get("image_title")
        if image_title is not None:
            s = str(image_title).strip()
            if s:
                parts.append(s)

        if asset.get("content_type") == "image":
            surrounding = metadata.get("surrounding_text")
            if surrounding is not None:
                s = str(surrounding).strip()
                if s:
                    parts.append(s)
            summary = (asset.get("summary") or "").strip()
            if summary:
                parts.append(summary)

        return "\n".join(parts)

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
