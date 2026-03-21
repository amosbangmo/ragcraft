from __future__ import annotations

import numpy as np

# Local sentence-transformers model (see requirements.txt). Same family as common RAG eval setups.
_DEFAULT_MODEL_NAME = "all-MiniLM-L6-v2"


class SemanticSimilarityService:
    """
    Embedding-based cosine similarity between two answer strings (e.g. generated vs gold).

    Uses sentence-transformers with lazy model load. Failures return 0.0.
    """

    def __init__(self, *, model_name: str | None = None) -> None:
        self._model_name = (model_name or _DEFAULT_MODEL_NAME).strip() or _DEFAULT_MODEL_NAME
        self._model = None

    @property
    def model_name(self) -> str:
        return self._model_name

    def _get_model(self):
        if self._model is None:
            from sentence_transformers import SentenceTransformer

            self._model = SentenceTransformer(self._model_name)
        return self._model

    def compute_similarity(self, answer: str, expected_answer: str) -> float:
        a = (answer or "").strip()
        b = (expected_answer or "").strip()
        if not a or not b:
            return 0.0
        try:
            model = self._get_model()
            emb = model.encode(
                [a, b],
                normalize_embeddings=True,
                show_progress_bar=False,
            )
            cos = float(np.dot(emb[0], emb[1]))
            return max(0.0, min(1.0, cos))
        except Exception:
            return 0.0
