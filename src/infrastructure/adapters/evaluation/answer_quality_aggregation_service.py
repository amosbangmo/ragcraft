"""Token-overlap precision / recall / F1 between generated and expected answers (deterministic)."""

from __future__ import annotations

import re


class AnswerQualityAggregationService:
    def normalize_text(self, text: str) -> str:
        normalized = re.sub(r"\s+", " ", (text or "").strip().lower())
        normalized = re.sub(r"[^a-z0-9àâçéèêëîïôûùüÿñæœ\s_-]", "", normalized)
        return normalized.strip()

    def tokenize_text(self, text: str) -> list[str]:
        normalized = self.normalize_text(text)
        if not normalized:
            return []
        return [token for token in normalized.split(" ") if token]

    def compute_answer_precision_recall_f1(
        self,
        *,
        generated_answer: str,
        expected_answer: str,
    ) -> tuple[float, float, float]:
        generated_tokens = self.tokenize_text(generated_answer)
        expected_tokens = self.tokenize_text(expected_answer)

        if not generated_tokens or not expected_tokens:
            return 0.0, 0.0, 0.0

        generated_counts: dict[str, int] = {}
        expected_counts: dict[str, int] = {}

        for token in generated_tokens:
            generated_counts[token] = generated_counts.get(token, 0) + 1

        for token in expected_tokens:
            expected_counts[token] = expected_counts.get(token, 0) + 1

        overlap = 0
        for token, count in generated_counts.items():
            overlap += min(count, expected_counts.get(token, 0))

        if overlap == 0:
            return 0.0, 0.0, 0.0

        precision = overlap / len(generated_tokens)
        recall = overlap / len(expected_tokens)

        if precision + recall == 0:
            f1 = 0.0
        else:
            f1 = 2 * precision * recall / (precision + recall)

        return precision, recall, f1
