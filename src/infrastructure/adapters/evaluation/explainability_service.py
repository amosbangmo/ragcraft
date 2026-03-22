from __future__ import annotations

from typing import Any

from src.infrastructure.adapters.evaluation.llm_judge_service import JUDGE_FAILURE_REASON


def _is_score(value: object) -> bool:
    """True for numeric scores; excludes bool (subclass of int in Python)."""
    return isinstance(value, (int, float)) and not isinstance(value, bool)


class ExplainabilityService:
    """
    Generate human-readable explanations and debugging hints for each benchmark row
    based on metrics and pipeline status. Rule-based only (no extra LLM calls).
    """

    def build_explanation(self, row: dict[str, Any]) -> dict[str, Any]:
        explanations: list[str] = []
        suggestions: list[str] = []

        if row.get("pipeline_failed"):
            explanations.append("The answer pipeline did not complete for this row.")
            suggestions.append(
                "Check pipeline logs, connectivity, timeouts, and upstream retrieval or LLM errors."
            )
            return {"explanations": explanations, "suggestions": suggestions}

        judge_failed = row.get("judge_failed") is True
        if judge_failed:
            explanations.append(
                "LLM judge failed for this row; judge-based scores are unavailable."
            )
            jr = row.get("judge_failure_reason")
            if (
                isinstance(jr, str)
                and jr.strip()
                and jr.strip() != JUDGE_FAILURE_REASON
            ):
                explanations.append(f"Judge failure reason: {jr.strip()}.")
            suggestions.append(
                "Retry evaluation after checking judge model configuration, connectivity, and provider responses."
            )

        recall = row.get("recall_at_k")
        groundedness = row.get("groundedness_score")
        relevance = row.get("answer_relevance_score")
        confidence = row.get("confidence")
        answer_f1 = row.get("answer_f1")
        prompt_precision = row.get("prompt_doc_id_precision")
        citation_recall = row.get("citation_doc_id_recall")
        hallucination = row.get("has_hallucination")

        if _is_score(recall) and float(recall) < 0.5:
            explanations.append("Relevant documents were not retrieved (low recall@K).")
            suggestions.append("Improve retrieval (chunking, embeddings, hybrid search).")

        if _is_score(prompt_precision) and float(prompt_precision) < 0.5:
            explanations.append("Prompt contains many irrelevant documents.")
            suggestions.append("Improve reranking or filtering before prompt construction.")

        if _is_score(citation_recall) and float(citation_recall) < 0.5:
            explanations.append("Answer does not cite expected sources.")
            suggestions.append("Improve citation grounding or prompt instructions.")

        if not judge_failed:
            if _is_score(groundedness) and float(groundedness) < 0.5:
                explanations.append("Answer is weakly grounded in retrieved context.")
                suggestions.append("Ensure retrieved context is actually used in generation.")

            if _is_score(relevance) and float(relevance) < 0.5:
                explanations.append("Answer does not properly address the question.")
                suggestions.append("Improve prompt instructions or query understanding.")

            if bool(hallucination):
                explanations.append("Answer likely contains hallucinated content.")
                suggestions.append("Increase grounding constraints or reduce generation temperature.")

        if (
            _is_score(confidence)
            and _is_score(answer_f1)
            and float(confidence) > 0.7
            and float(answer_f1) < 0.5
        ):
            explanations.append("Model is overconfident despite low correctness.")
            suggestions.append("Recalibrate confidence scoring or adjust thresholds.")

        return {
            "explanations": explanations,
            "suggestions": suggestions,
        }
