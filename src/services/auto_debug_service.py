from __future__ import annotations

from typing import Any


def _is_score(value: object) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool)


class AutoDebugService:
    """
    Produce system-level debugging suggestions from aggregated summary metrics
    and failure-analysis counts. Rule-based only (no LLM calls).
    """

    def build_suggestions(
        self,
        summary: dict[str, Any],
        failures: dict[str, Any] | None,
    ) -> list[dict[str, str]]:
        suggestions: list[dict[str, str]] = []

        def add(title: str, description: str) -> None:
            suggestions.append({"title": title, "description": description})

        recall = summary.get("avg_recall_at_k")
        if _is_score(recall) and float(recall) < 0.5:
            add(
                "Improve retrieval recall",
                "Low recall@K suggests missing relevant documents. Try better chunking, embeddings, or hybrid search.",
            )

        groundedness = summary.get("avg_groundedness_score")
        if _is_score(groundedness) and float(groundedness) < 0.5:
            add(
                "Improve grounding",
                "Answers are weakly grounded. Ensure retrieved context is used in the prompt and reduce irrelevant documents.",
            )

        citation_recall = summary.get("avg_citation_doc_id_recall")
        if _is_score(citation_recall) and float(citation_recall) < 0.5:
            add(
                "Improve citation coverage",
                "Answers are not citing expected sources. Strengthen citation instructions or enforce grounding.",
            )

        halluc_rate = summary.get("hallucination_rate")
        if _is_score(halluc_rate) and float(halluc_rate) > 0.3:
            add(
                "Reduce hallucinations",
                "High hallucination rate detected. Lower generation temperature or strengthen grounding constraints.",
            )

        conf = summary.get("avg_confidence")
        f1 = summary.get("avg_answer_f1")
        if (
            _is_score(conf)
            and _is_score(f1)
            and float(conf) > 0.7
            and float(f1) < 0.5
        ):
            add(
                "Fix overconfidence",
                "Model confidence is high despite low correctness. Recalibrate confidence scoring or thresholds.",
            )

        if isinstance(failures, dict):
            counts = failures.get("counts")
            if not isinstance(counts, dict):
                counts = {}

            if int(counts.get("retrieval_failure", 0) or 0) > 0:
                add(
                    "Retrieval failures detected",
                    "Some queries fail to retrieve relevant documents. Review indexing and retrieval configuration.",
                )

            if int(counts.get("context_selection_failure", 0) or 0) > 0:
                add(
                    "Context selection issues",
                    "Prompt contains irrelevant documents. Improve reranking or filtering.",
                )

            if int(counts.get("citation_failure", 0) or 0) > 0:
                add(
                    "Citation issues",
                    "Answers do not properly cite sources. Improve prompt formatting or enforce citations.",
                )

        return suggestions
