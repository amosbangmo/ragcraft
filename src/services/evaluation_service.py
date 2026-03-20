import re
from collections import Counter

import numpy as np


class EvaluationService:
    def compute_confidence(self, reranked_assets: list) -> float:
        if not reranked_assets:
            return 0.0

        scores: list[float] = []

        for item in reranked_assets:
            metadata = self._confidence_metadata(item)
            score = metadata.get("rerank_score")
            normalized_score = 1 / (1 + np.exp(-score))
            if score is not None:
                scores.append(float(normalized_score))

        if not scores:
            return 0.0

        confidence = float(np.mean(scores))

        return round(confidence, 2)

    def _confidence_metadata(self, item) -> dict:
        if isinstance(item, dict):
            meta = item.get("metadata")
            return meta if isinstance(meta, dict) else {}
        return getattr(item, "metadata", None) or {}

    def evaluate_gold_qa_dataset(
        self,
        *,
        entries,
        pipeline_runner,
    ) -> dict:
        rows: list[dict] = []

        doc_id_recall_values: list[float] = []
        source_recall_values: list[float] = []
        precision_at_k_values: list[float] = []
        reciprocal_rank_values: list[float] = []
        average_precision_values: list[float] = []
        confidence_values: list[float] = []
        latency_values: list[float] = []

        answer_precision_values: list[float] = []
        answer_recall_values: list[float] = []
        answer_f1_values: list[float] = []
        exact_match_hits = 0

        entries_with_expected_doc_ids = 0
        entries_with_expected_sources = 0
        entries_with_expected_answers = 0
        doc_id_hits = 0
        source_hits = 0
        successful_queries = 0

        for entry in entries:
            result = pipeline_runner(entry)
            pipeline = result.get("pipeline")
            answer = (result.get("answer") or "").strip()
            latency_ms = float(result.get("latency_ms", 0.0))

            expected_doc_ids = set(entry.expected_doc_ids or [])
            expected_sources = set(entry.expected_sources or [])
            expected_answer = (entry.expected_answer or "").strip()

            if expected_doc_ids:
                entries_with_expected_doc_ids += 1

            if expected_sources:
                entries_with_expected_sources += 1

            if expected_answer:
                entries_with_expected_answers += 1

            correctness = self._compute_answer_correctness(
                answer=answer,
                expected_answer=expected_answer,
            )

            if expected_answer:
                answer_precision_values.append(correctness["answer_precision"])
                answer_recall_values.append(correctness["answer_recall"])
                answer_f1_values.append(correctness["answer_f1"])
                if correctness["answer_exact_match"]:
                    exact_match_hits += 1

            if pipeline is None:
                row = {
                    "entry_id": entry.id,
                    "question": entry.question,
                    "answer_preview": answer[:220],
                    "expected_answer_present": bool(expected_answer),
                    "answer_exact_match": bool(correctness["answer_exact_match"]),
                    "answer_precision": round(correctness["answer_precision"], 2),
                    "answer_recall": round(correctness["answer_recall"], 2),
                    "answer_f1": round(correctness["answer_f1"], 2),
                    "expected_doc_ids_count": len(expected_doc_ids),
                    "retrieved_doc_ids_count": 0,
                    "doc_id_overlap_count": 0,
                    "doc_id_recall": 0.0,
                    "precision_at_k": 0.0,
                    "reciprocal_rank": 0.0,
                    "average_precision": 0.0,
                    "expected_sources_count": len(expected_sources),
                    "retrieved_sources_count": 0,
                    "source_overlap_count": 0,
                    "source_recall": 0.0,
                    "confidence": 0.0,
                    "latency_ms": round(latency_ms, 1),
                    "retrieval_mode": "none",
                    "query_rewrite_enabled": False,
                    "hybrid_retrieval_enabled": False,
                }
                rows.append(row)
                latency_values.append(latency_ms)
                continue

            successful_queries += 1

            ranked_doc_ids = [
                doc_id
                for doc_id in pipeline.get("selected_doc_ids", [])
                if doc_id
            ]
            selected_doc_ids = set(ranked_doc_ids)

            source_references = pipeline.get("source_references", []) or []
            selected_sources = {
                ref.get("source_file")
                for ref in source_references
                if ref.get("source_file")
            }

            doc_id_overlap_count = len(selected_doc_ids.intersection(expected_doc_ids))
            source_overlap_count = len(selected_sources.intersection(expected_sources))

            doc_id_recall = 0.0
            source_recall = 0.0
            precision_at_k = 0.0
            reciprocal_rank = 0.0
            average_precision = 0.0

            if expected_doc_ids:
                doc_id_recall = doc_id_overlap_count / len(expected_doc_ids)
                precision_at_k = self._compute_precision_at_k(
                    ranked_doc_ids=ranked_doc_ids,
                    expected_doc_ids=expected_doc_ids,
                )
                reciprocal_rank = self._compute_reciprocal_rank(
                    ranked_doc_ids=ranked_doc_ids,
                    expected_doc_ids=expected_doc_ids,
                )
                average_precision = self._compute_average_precision(
                    ranked_doc_ids=ranked_doc_ids,
                    expected_doc_ids=expected_doc_ids,
                )

                doc_id_recall_values.append(doc_id_recall)
                precision_at_k_values.append(precision_at_k)
                reciprocal_rank_values.append(reciprocal_rank)
                average_precision_values.append(average_precision)

                if doc_id_overlap_count > 0:
                    doc_id_hits += 1

            if expected_sources:
                source_recall = source_overlap_count / len(expected_sources)
                source_recall_values.append(source_recall)
                if source_overlap_count > 0:
                    source_hits += 1

            confidence = float(pipeline.get("confidence", 0.0))
            confidence_values.append(confidence)
            latency_values.append(latency_ms)

            row = {
                "entry_id": entry.id,
                "question": entry.question,
                "answer_preview": answer[:220],
                "expected_answer_present": bool(expected_answer),
                "answer_exact_match": bool(correctness["answer_exact_match"]),
                "answer_precision": round(correctness["answer_precision"], 2),
                "answer_recall": round(correctness["answer_recall"], 2),
                "answer_f1": round(correctness["answer_f1"], 2),
                "expected_doc_ids_count": len(expected_doc_ids),
                "retrieved_doc_ids_count": len(selected_doc_ids),
                "doc_id_overlap_count": doc_id_overlap_count,
                "doc_id_recall": round(doc_id_recall, 2),
                "precision_at_k": round(precision_at_k, 2),
                "reciprocal_rank": round(reciprocal_rank, 2),
                "average_precision": round(average_precision, 2),
                "expected_sources_count": len(expected_sources),
                "retrieved_sources_count": len(selected_sources),
                "source_overlap_count": source_overlap_count,
                "source_recall": round(source_recall, 2),
                "confidence": round(confidence, 2),
                "latency_ms": round(latency_ms, 1),
                "retrieval_mode": pipeline.get("retrieval_mode", "unknown"),
                "query_rewrite_enabled": bool(pipeline.get("query_rewrite_enabled", False)),
                "hybrid_retrieval_enabled": bool(pipeline.get("hybrid_retrieval_enabled", False)),
            }
            rows.append(row)

        summary = {
            "total_entries": len(rows),
            "successful_queries": successful_queries,
            "entries_with_expected_doc_ids": entries_with_expected_doc_ids,
            "entries_with_expected_sources": entries_with_expected_sources,
            "entries_with_expected_answers": entries_with_expected_answers,
            "avg_doc_id_recall": round(float(np.mean(doc_id_recall_values)), 2) if doc_id_recall_values else 0.0,
            "avg_source_recall": round(float(np.mean(source_recall_values)), 2) if source_recall_values else 0.0,
            "avg_precision_at_k": round(float(np.mean(precision_at_k_values)), 2) if precision_at_k_values else 0.0,
            "mrr": round(float(np.mean(reciprocal_rank_values)), 2) if reciprocal_rank_values else 0.0,
            "map": round(float(np.mean(average_precision_values)), 2) if average_precision_values else 0.0,
            "avg_answer_precision": round(float(np.mean(answer_precision_values)), 2) if answer_precision_values else 0.0,
            "avg_answer_recall": round(float(np.mean(answer_recall_values)), 2) if answer_recall_values else 0.0,
            "avg_answer_f1": round(float(np.mean(answer_f1_values)), 2) if answer_f1_values else 0.0,
            "answer_exact_match_rate": round(exact_match_hits / entries_with_expected_answers, 2)
            if entries_with_expected_answers
            else 0.0,
            "avg_confidence": round(float(np.mean(confidence_values)), 2) if confidence_values else 0.0,
            "avg_latency_ms": round(float(np.mean(latency_values)), 1) if latency_values else 0.0,
            "doc_id_hit_rate": round(doc_id_hits / entries_with_expected_doc_ids, 2)
            if entries_with_expected_doc_ids
            else 0.0,
            "source_hit_rate": round(source_hits / entries_with_expected_sources, 2)
            if entries_with_expected_sources
            else 0.0,
        }

        return {
            "summary": summary,
            "rows": rows,
        }

    def _compute_answer_correctness(
        self,
        *,
        answer: str,
        expected_answer: str,
    ) -> dict:
        normalized_answer = self._normalize_text(answer)
        normalized_expected = self._normalize_text(expected_answer)

        if not normalized_expected:
            return {
                "answer_exact_match": False,
                "answer_precision": 0.0,
                "answer_recall": 0.0,
                "answer_f1": 0.0,
            }

        exact_match = normalized_answer == normalized_expected

        answer_tokens = self._tokenize(normalized_answer)
        expected_tokens = self._tokenize(normalized_expected)

        if not answer_tokens and not expected_tokens:
            precision = 1.0
            recall = 1.0
            f1 = 1.0
        elif not answer_tokens or not expected_tokens:
            precision = 0.0
            recall = 0.0
            f1 = 0.0
        else:
            overlap = sum((Counter(answer_tokens) & Counter(expected_tokens)).values())
            precision = overlap / len(answer_tokens) if answer_tokens else 0.0
            recall = overlap / len(expected_tokens) if expected_tokens else 0.0
            if precision + recall == 0:
                f1 = 0.0
            else:
                f1 = 2 * precision * recall / (precision + recall)

        return {
            "answer_exact_match": exact_match,
            "answer_precision": float(precision),
            "answer_recall": float(recall),
            "answer_f1": float(f1),
        }

    def _normalize_text(self, text: str) -> str:
        cleaned = (text or "").strip().lower()
        cleaned = re.sub(r"\s+", " ", cleaned)
        cleaned = re.sub(r"[^\w\s]", "", cleaned)
        return cleaned.strip()

    def _tokenize(self, text: str) -> list[str]:
        return [token for token in text.split() if token]

    def _compute_precision_at_k(
        self,
        *,
        ranked_doc_ids: list[str],
        expected_doc_ids: set[str],
    ) -> float:
        if not ranked_doc_ids:
            return 0.0

        relevant_retrieved = sum(1 for doc_id in ranked_doc_ids if doc_id in expected_doc_ids)
        return relevant_retrieved / len(ranked_doc_ids)

    def _compute_reciprocal_rank(
        self,
        *,
        ranked_doc_ids: list[str],
        expected_doc_ids: set[str],
    ) -> float:
        for index, doc_id in enumerate(ranked_doc_ids, start=1):
            if doc_id in expected_doc_ids:
                return 1.0 / index
        return 0.0

    def _compute_average_precision(
        self,
        *,
        ranked_doc_ids: list[str],
        expected_doc_ids: set[str],
    ) -> float:
        if not ranked_doc_ids or not expected_doc_ids:
            return 0.0

        precision_sum = 0.0
        relevant_found = 0

        for index, doc_id in enumerate(ranked_doc_ids, start=1):
            if doc_id not in expected_doc_ids:
                continue

            relevant_found += 1
            precision_at_index = relevant_found / index
            precision_sum += precision_at_index

        if relevant_found == 0:
            return 0.0

        return precision_sum / len(expected_doc_ids)
