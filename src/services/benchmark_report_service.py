from __future__ import annotations

import csv
import io
import json
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

from src.domain.benchmark_result import BenchmarkResult, BenchmarkRunMetadata


def _utc_timestamp_for_filename(when: datetime) -> str:
    if when.tzinfo is None:
        when = when.replace(tzinfo=timezone.utc)
    else:
        when = when.astimezone(timezone.utc)
    return when.strftime("%Y%m%dT%H%M%SZ")


def _iso_utc(when: datetime) -> str:
    if when.tzinfo is None:
        when = when.replace(tzinfo=timezone.utc)
    else:
        when = when.astimezone(timezone.utc)
    return when.isoformat().replace("+00:00", "Z")


def safe_filename_segment(value: str, *, max_length: int = 80) -> str:
    cleaned = re.sub(r"[^\w.\-]+", "_", (value or "").strip(), flags=re.UNICODE)
    cleaned = cleaned.strip("._") or "project"
    return cleaned[:max_length]


def _cell_csv(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, (list, tuple, set, dict)):
        return json.dumps(value, ensure_ascii=False, separators=(",", ":"))
    return str(value)


def _json_default(obj: Any) -> Any:
    if isinstance(obj, (str, int, float, bool)) or obj is None:
        return obj
    return str(obj)


def _sorted_row_keys(rows: list[dict[str, Any]]) -> list[str]:
    keys: set[str] = set()
    for row in rows:
        keys.update(k for k in row.keys() if k not in {"entry_id", "question"})
    return sorted(keys)


def _markdown_escape_cell(text: str, *, max_len: int = 120) -> str:
    raw = (text or "").replace("|", "\\|").replace("\n", " ").strip()
    if len(raw) > max_len:
        return raw[: max_len - 1] + "…"
    return raw


@dataclass(frozen=True)
class BenchmarkExportArtifacts:
    metadata: BenchmarkRunMetadata
    json_bytes: bytes
    json_filename: str
    csv_bytes: bytes
    csv_filename: str
    markdown_bytes: bytes
    markdown_filename: str


class BenchmarkReportService:
    """
    Serializes structured ``BenchmarkResult`` payloads into downloadable reports.

    Keeps Streamlit pages thin by centralizing JSON / CSV / Markdown formatting.
    """

    def build_export_artifacts(
        self,
        *,
        project_id: str,
        result: BenchmarkResult,
        enable_query_rewrite: bool,
        enable_hybrid_retrieval: bool,
        generated_at: datetime | None = None,
    ) -> BenchmarkExportArtifacts:
        when = generated_at or datetime.now(timezone.utc)
        ts_file = _utc_timestamp_for_filename(when)
        ts_meta = _iso_utc(when)

        safe_project = safe_filename_segment(project_id)
        metadata = BenchmarkRunMetadata(
            project_id=project_id,
            generated_at_utc=ts_meta,
            enable_query_rewrite=enable_query_rewrite,
            enable_hybrid_retrieval=enable_hybrid_retrieval,
        )

        json_bytes = self._build_json_bytes(metadata=metadata, result=result)
        csv_bytes = self._build_csv_bytes(result=result)
        md_bytes = self._build_markdown_bytes(
            metadata=metadata,
            result=result,
        )

        return BenchmarkExportArtifacts(
            metadata=metadata,
            json_bytes=json_bytes,
            json_filename=f"ragcraft_benchmark_{safe_project}_json_{ts_file}.json",
            csv_bytes=csv_bytes,
            csv_filename=f"ragcraft_benchmark_{safe_project}_csv_{ts_file}.csv",
            markdown_bytes=md_bytes,
            markdown_filename=f"ragcraft_benchmark_{safe_project}_md_{ts_file}.md",
        )

    def _build_json_bytes(self, *, metadata: BenchmarkRunMetadata, result: BenchmarkResult) -> bytes:
        payload = {
            "metadata": metadata.to_dict(),
            "summary": result.summary.to_dict(),
            "rows": [row.to_dict() for row in result.rows],
        }
        if result.correlations is not None:
            payload["correlations"] = dict(result.correlations)
        if result.failures is not None:
            payload["failures"] = dict(result.failures)
        text = json.dumps(payload, indent=2, ensure_ascii=False, default=_json_default)
        return text.encode("utf-8")

    def _build_csv_bytes(self, *, result: BenchmarkResult) -> bytes:
        row_dicts = [row.to_dict() for row in result.rows]
        extra_keys = _sorted_row_keys(row_dicts)
        header = ["entry_id", "question", *extra_keys]

        buffer = io.StringIO(newline="")
        writer = csv.writer(buffer, quoting=csv.QUOTE_MINIMAL, lineterminator="\n")
        writer.writerow(header)

        for row in row_dicts:
            writer.writerow(
                [
                    _cell_csv(row.get("entry_id")),
                    _cell_csv(row.get("question")),
                    *(_cell_csv(row.get(k)) for k in extra_keys),
                ]
            )

        return buffer.getvalue().encode("utf-8-sig")

    def _build_markdown_bytes(self, *, metadata: BenchmarkRunMetadata, result: BenchmarkResult) -> bytes:
        summary = result.summary.to_dict()
        lines: list[str] = [
            "# RAGCraft benchmark report",
            "",
            "## Run context",
            "",
            f"- **Project ID:** `{_markdown_escape_cell(metadata.project_id, max_len=500)}`",
            f"- **Generated (UTC):** {metadata.generated_at_utc}",
            f"- **Query rewrite:** {'on' if metadata.enable_query_rewrite else 'off'}",
            f"- **Hybrid retrieval:** {'on' if metadata.enable_hybrid_retrieval else 'off'}",
            "",
            "## Summary metrics",
            "",
        ]

        summary_items = sorted(summary.items(), key=lambda item: item[0])
        for key, value in summary_items:
            lines.append(f"- **{key}:** {value}")
        lines.append("")
        lines.append("## Per-entry results")
        lines.append("")

        if not result.rows:
            lines.append("_No benchmark rows._")
        else:
            preferred_cols = [
                "entry_id",
                "question",
                "recall_at_k",
                "precision_at_k",
                "reciprocal_rank",
                "average_precision",
                "hit_at_k",
                "source_recall",
                "prompt_doc_id_precision",
                "prompt_doc_id_recall",
                "prompt_doc_id_f1",
                "prompt_doc_id_hit_rate",
                "citation_doc_id_precision",
                "citation_doc_id_recall",
                "citation_doc_id_f1",
                "citation_doc_id_hit_rate",
                "citation_doc_ids_count",
                "citation_doc_id_overlap_count",
                "answer_f1",
                "groundedness_score",
                "citation_faithfulness_score",
                "answer_relevance_score",
                "hallucination_score",
                "has_hallucination",
                "confidence",
                "latency_ms",
            ]
            row_dicts = [r.to_dict() for r in result.rows]
            all_keys: set[str] = set()
            for d in row_dicts:
                all_keys.update(d.keys())
            table_cols = [c for c in preferred_cols if c in all_keys]
            for k in sorted(all_keys):
                if k not in table_cols:
                    table_cols.append(k)

            lines.append("| " + " | ".join(table_cols) + " |")
            lines.append("| " + " | ".join("---" for _ in table_cols) + " |")
            for d in row_dicts:
                cells = []
                for col in table_cols:
                    val = d.get(col, "")
                    if col == "question":
                        cells.append(_markdown_escape_cell(str(val)))
                    else:
                        cells.append(_markdown_escape_cell(str(val), max_len=80))
                lines.append("| " + " | ".join(cells) + " |")

        text = "\n".join(lines) + "\n"
        return text.encode("utf-8")

