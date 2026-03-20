import numpy as np


class EvaluationService:
    def compute_confidence(self, docs, reranked_assets=None) -> float:
        if not docs:
            return 0.0

        scores = []

        for doc in docs:
            score = doc.metadata.get("score", 0.5)
            scores.append(score)

        confidence = float(np.mean(scores))
        return round(confidence, 2)

    def evaluate_gold_qa_dataset(
        self,
        *,
        entries,
        pipeline_runner,
    ) -> dict:
        rows: list[dict] = []

        doc_id_recall_values: list[float] = []
        source_recall_values: list[float] = []
        confidence_values: list[float] = []
        latency_values: list[float] = []

        entries_with_expected_doc_ids = 0
        entries_with_expected_sources = 0
        doc_id_hits = 0
        source_hits = 0
        successful_queries = 0

        for entry in entries:
            result = pipeline_runner(entry)
            pipeline = result.get("pipeline")
            latency_ms = float(result.get("latency_ms", 0.0))

            expected_doc_ids = set(entry.expected_doc_ids or [])
            expected_sources = set(entry.expected_sources or [])

            if expected_doc_ids:
                entries_with_expected_doc_ids += 1

            if expected_sources:
                entries_with_expected_sources += 1

            if pipeline is None:
                row = {
                    "entry_id": entry.id,
                    "question": entry.question,
                    "expected_doc_ids_count": len(expected_doc_ids),
                    "retrieved_doc_ids_count": 0,
                    "doc_id_overlap_count": 0,
                    "doc_id_recall": 0.0,
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

            selected_doc_ids = set(pipeline.get("selected_doc_ids", []))
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

            if expected_doc_ids:
                doc_id_recall = doc_id_overlap_count / len(expected_doc_ids)
                doc_id_recall_values.append(doc_id_recall)
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
                "expected_doc_ids_count": len(expected_doc_ids),
                "retrieved_doc_ids_count": len(selected_doc_ids),
                "doc_id_overlap_count": doc_id_overlap_count,
                "doc_id_recall": round(doc_id_recall, 2),
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
            "avg_doc_id_recall": round(float(np.mean(doc_id_recall_values)), 2) if doc_id_recall_values else 0.0,
            "avg_source_recall": round(float(np.mean(source_recall_values)), 2) if source_recall_values else 0.0,
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
