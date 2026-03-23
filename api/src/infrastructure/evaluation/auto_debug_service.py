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
        seen_desc_norm: set[str] = set()

        def add(title: str, description: str) -> None:
            t = title.strip()
            d = description.strip()
            if not t and not d:
                return
            norm = " ".join(d.lower().split()) if d else t.lower()
            if norm in seen_desc_norm:
                return
            seen_desc_norm.add(norm)
            suggestions.append({"title": t, "description": d})

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
        if _is_score(conf) and _is_score(f1) and float(conf) > 0.7 and float(f1) < 0.5:
            add(
                "Fix overconfidence",
                "Model confidence is high despite low correctness. Recalibrate confidence scoring or thresholds.",
            )

        pfr = summary.get("pipeline_failure_rate")
        if _is_score(pfr) and float(pfr) >= 0.1:
            add(
                "Reduce pipeline failures",
                "A noticeable share of rows did not complete the answer pipeline. Check timeouts, model errors, "
                "and retrieval stability — this is separate from LLM judge scoring issues.",
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

            jf = int(counts.get("judge_failure", 0) or 0)
            if jf > 0:
                add(
                    "LLM judge call failures",
                    f"{jf} row(s) could not be scored by the judge. Retry evaluation, verify judge model settings, "
                    "and inspect API responses — do not treat these rows as grounding or hallucination regressions.",
                )

        return suggestions
