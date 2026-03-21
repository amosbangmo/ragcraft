"""
Evaluation and QA dataset API models.

``X-User-Id`` supplies workspace identity (see :func:`apps.api.dependencies.get_request_user_id`).
``project_id`` is passed in the body or as a query parameter per route.
"""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field


# --- Manual evaluation ---


class ManualEvaluationRequest(BaseModel):
    model_config = {"extra": "forbid"}

    project_id: str = Field(..., min_length=1)
    question: str = Field(..., min_length=1)
    expected_answer: str | None = None
    expected_doc_ids: list[str] = Field(default_factory=list)
    expected_sources: list[str] = Field(default_factory=list)
    enable_query_rewrite_override: bool | None = Field(
        default=None,
        description="If set, overrides project default for query rewrite for this run.",
    )
    enable_hybrid_retrieval_override: bool | None = Field(
        default=None,
        description="If set, overrides project default for hybrid retrieval for this run.",
    )


class ManualEvaluationResponse(BaseModel):
    """Structured manual eval result (same keys as :meth:`ManualEvaluationResult.to_dict`)."""

    model_config = {"extra": "forbid"}

    question: str
    answer: str
    expected_answer: str | None = None
    confidence: float = 0.0
    pipeline_failed: bool = False
    judge_failed: bool = False
    judge_failure_reason: str | None = None
    prompt_sources: list[dict[str, Any]] = Field(default_factory=list)
    raw_assets: list[dict[str, Any]] = Field(default_factory=list)
    answer_quality: dict[str, Any] | None = None
    answer_citation_quality: dict[str, Any] | None = None
    prompt_source_quality: dict[str, Any] | None = None
    retrieval_quality: dict[str, Any] | None = None
    pipeline_signals: dict[str, Any] | None = None
    expectation_comparison: dict[str, Any] | None = None
    detected_issues: list[str] = Field(default_factory=list)


# --- Gold QA benchmark run ---


class DatasetBenchmarkRunRequest(BaseModel):
    model_config = {"extra": "forbid"}

    project_id: str = Field(..., min_length=1)
    enable_query_rewrite: bool = Field(
        description="Fixed override for every row in the benchmark (same as Streamlit run).",
    )
    enable_hybrid_retrieval: bool = Field(
        description="Fixed override for hybrid retrieval for every row.",
    )


class BenchmarkResultResponse(BaseModel):
    """Full benchmark payload (:class:`~src.domain.benchmark_result.BenchmarkResult.to_dict`)."""

    model_config = {"extra": "forbid"}

    summary: dict[str, Any] = Field(default_factory=dict)
    rows: list[dict[str, Any]] = Field(default_factory=list)
    correlations: dict[str, Any] | None = None
    failures: dict[str, Any] | None = None
    multimodal_metrics: dict[str, Any] | None = None
    auto_debug: list[dict[str, str]] | None = None
    run_id: str | None = None


# --- QA dataset CRUD ---


class QaDatasetEntryResponse(BaseModel):
    model_config = {"extra": "forbid"}

    id: int
    user_id: str
    project_id: str
    question: str
    expected_answer: str | None = None
    expected_doc_ids: list[str] = Field(default_factory=list)
    expected_sources: list[str] = Field(default_factory=list)
    created_at: str | None = None
    updated_at: str | None = None


class QaDatasetEntryListResponse(BaseModel):
    model_config = {"extra": "forbid"}

    entries: list[QaDatasetEntryResponse] = Field(default_factory=list)


class QaDatasetEntryCreateRequest(BaseModel):
    model_config = {"extra": "forbid"}

    project_id: str = Field(..., min_length=1)
    question: str = Field(..., min_length=1)
    expected_answer: str | None = None
    expected_doc_ids: list[str] = Field(default_factory=list)
    expected_sources: list[str] = Field(default_factory=list)


class QaDatasetEntryUpdateRequest(BaseModel):
    model_config = {"extra": "forbid"}

    project_id: str = Field(..., min_length=1, description="Scope for row update.")
    question: str = Field(..., min_length=1)
    expected_answer: str | None = None
    expected_doc_ids: list[str] = Field(default_factory=list)
    expected_sources: list[str] = Field(default_factory=list)


class QaDatasetEntryDeleteResponse(BaseModel):
    model_config = {"extra": "forbid"}

    deleted: bool = True
    entry_id: int


# --- Generate dataset ---


class QaDatasetGenerateRequest(BaseModel):
    model_config = {"extra": "forbid"}

    project_id: str = Field(..., min_length=1)
    num_questions: int = Field(..., ge=1, le=500)
    source_files: list[str] | None = Field(
        default=None,
        description="Optional subset of project source filenames; omit to use project defaults.",
    )
    generation_mode: Literal["append", "replace", "append_dedup"] = "append"


class QaDatasetGenerateResponse(BaseModel):
    model_config = {"extra": "forbid"}

    generation_mode: str
    deleted_existing_entries: int = 0
    created_entries: list[QaDatasetEntryResponse] = Field(default_factory=list)
    skipped_duplicates: list[str] = Field(default_factory=list)
    requested_questions: int = 0
    raw_generated_count: int = 0


# --- Query / retrieval logs ---


class RetrievalLogsResponse(BaseModel):
    model_config = {"extra": "forbid"}

    entries: list[dict[str, Any]] = Field(
        default_factory=list,
        description="Rows from SQLite query log store (newest-first depends on repository).",
    )


# --- Export stub ---


class BenchmarkExportStubResponse(BaseModel):
    model_config = {"extra": "forbid"}

    implemented: bool = False
    message: str = Field(
        default="Benchmark export via API is not implemented yet; use the same "
        "BuildBenchmarkExportArtifactsUseCase from a client job or Streamlit.",
    )
    planned_post_path: str = "/evaluation/export/benchmark"
    formats: list[str] = Field(default_factory=lambda: ["json", "csv", "markdown"])
