import math


class EvaluationService:
    """
    Lightweight confidence proxy for the current RAG pipeline.

    Goal:
    - remain simple and inexpensive
    - use retrieval signals when available
    - use reranking scores when available
    - return a stable 0..1 confidence value for the UI
    """

    DEFAULT_RETRIEVAL_SCORE = 0.5
    RETRIEVAL_WEIGHT = 0.35
    RERANK_WEIGHT = 0.65

    def compute_confidence(
        self,
        docs: list | None,
        reranked_assets: list[dict] | None = None,
    ) -> float:
        retrieval_score = self._compute_retrieval_score(docs or [])
        rerank_score = self._compute_rerank_score(reranked_assets or [])

        if rerank_score is None:
            confidence = retrieval_score
        else:
            confidence = (
                retrieval_score * self.RETRIEVAL_WEIGHT
                + rerank_score * self.RERANK_WEIGHT
            )

        confidence = max(0.0, min(1.0, float(confidence)))
        return round(confidence, 2)

    def _compute_retrieval_score(self, docs: list) -> float:
        if not docs:
            return 0.0

        normalized_scores: list[float] = []

        for doc in docs:
            metadata = getattr(doc, "metadata", {}) or {}

            raw_score = (
                metadata.get("score")
                or metadata.get("similarity_score")
                or metadata.get("retrieval_score")
            )

            normalized_scores.append(
                self._normalize_optional_score(raw_score, default=self.DEFAULT_RETRIEVAL_SCORE)
            )

        if not normalized_scores:
            return 0.0

        return sum(normalized_scores) / len(normalized_scores)

    def _compute_rerank_score(self, reranked_assets: list[dict]) -> float | None:
        if not reranked_assets:
            return None

        normalized_scores: list[float] = []

        for asset in reranked_assets:
            metadata = asset.get("metadata", {}) or {}
            raw_score = metadata.get("rerank_score")
            normalized_scores.append(
                self._normalize_optional_score(raw_score, default=0.5)
            )

        if not normalized_scores:
            return None

        return sum(normalized_scores) / len(normalized_scores)

    def _normalize_optional_score(self, raw_score, default: float) -> float:
        if raw_score is None:
            return default

        try:
            score = float(raw_score)
        except Exception:
            return default

        if 0.0 <= score <= 1.0:
            return score

        return self._sigmoid(score)

    def _sigmoid(self, value: float) -> float:
        try:
            return 1.0 / (1.0 + math.exp(-value))
        except OverflowError:
            return 0.0 if value < 0 else 1.0
