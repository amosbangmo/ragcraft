from __future__ import annotations

import logging

import numpy as np

logger = logging.getLogger(__name__)

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
        self._model_load_failed = False

    @property
    def model_name(self) -> str:
        return self._model_name

    def _get_model(self):
        if self._model_load_failed:
            return None
        if self._model is None:
            try:
                from sentence_transformers import SentenceTransformer

                self._model = SentenceTransformer(self._model_name)
            except Exception as e:
                logger.warning("Semantic similarity model load failed: %s", e)
                self._model_load_failed = True
                self._model = None
                return None
        return self._model

    def compute_similarity(self, answer: str, expected_answer: str) -> float:
        a = (answer or "").strip()
        b = (expected_answer or "").strip()
        if not a or not b:
            return 0.0
        if a == b:
            return 1.0
        try:
            model = self._get_model()
            if model is None:
                return 0.0
            emb = model.encode(
                [a, b],
                normalize_embeddings=True,
                show_progress_bar=False,
            )
            cos = float(np.dot(emb[0], emb[1]))
            return max(0.0, min(1.0, cos))
        except Exception as e:
            logger.warning("Semantic similarity failed: %s", e)
            return 0.0
