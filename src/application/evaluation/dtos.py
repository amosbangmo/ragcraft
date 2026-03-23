from __future__ import annotations

from dataclasses import dataclass

from src.domain.qa_dataset_entry import QADatasetEntry


@dataclass(frozen=True)
class RunManualEvaluationCommand:
    user_id: str
    project_id: str
    question: str
    expected_answer: str | None = None
    expected_doc_ids: list[str] | None = None
    expected_sources: list[str] | None = None
    enable_query_rewrite_override: bool | None = None
    enable_hybrid_retrieval_override: bool | None = None


@dataclass(frozen=True)
class RunGoldQaDatasetEvaluationCommand:
    user_id: str
    project_id: str
    enable_query_rewrite: bool
    enable_hybrid_retrieval: bool


@dataclass(frozen=True)
class ListRetrievalQueryLogsQuery:
    user_id: str
    project_id: str
    since_iso: str | None = None
    until_iso: str | None = None
    last_n: int | None = None


@dataclass(frozen=True)
class CreateQaDatasetEntryCommand:
    user_id: str
    project_id: str
    question: str
    expected_answer: str | None = None
    expected_doc_ids: list[str] | None = None
    expected_sources: list[str] | None = None


@dataclass(frozen=True)
class ListQaDatasetEntriesQuery:
    user_id: str
    project_id: str


@dataclass(frozen=True)
class UpdateQaDatasetEntryCommand:
    entry_id: int
    user_id: str
    project_id: str
    question: str
    expected_answer: str | None = None
    expected_doc_ids: list[str] | None = None
    expected_sources: list[str] | None = None


@dataclass(frozen=True)
class DeleteQaDatasetEntryCommand:
    entry_id: int
    user_id: str
    project_id: str


@dataclass(frozen=True)
class DeleteAllQaDatasetEntriesCommand:
    user_id: str
    project_id: str


@dataclass(frozen=True)
class GenerateQaDatasetCommand:
    user_id: str
    project_id: str
    num_questions: int
    source_files: list[str] | None = None
    generation_mode: str = "append"


@dataclass(frozen=True)
class GenerateQaDatasetResult:
    """Outcome of LLM-backed QA row generation and optional persistence."""

    generation_mode: str
    deleted_existing_entries: int
    created_entries: tuple[QADatasetEntry, ...]
    skipped_duplicates: tuple[str, ...]
    requested_questions: int
    raw_generated_count: int
