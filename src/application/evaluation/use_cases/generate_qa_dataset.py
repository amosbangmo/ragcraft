from __future__ import annotations

from src.domain.evaluation.qa_question_key import normalized_qa_question_key
from src.services.qa_dataset_generation_service import QADatasetGenerationService
from src.domain.ports import QADatasetEntriesPort

from .create_qa_dataset_entry import CreateQaDatasetEntryUseCase
from .delete_all_qa_dataset_entries import DeleteAllQaDatasetEntriesUseCase
from src.application.evaluation.dtos import GenerateQaDatasetCommand


class GenerateQaDatasetUseCase:
    """
    Orchestrates LLM-backed QA proposal generation and persistence modes (append / replace / dedup).
    LLM prompts and parsing live in :class:`~src.infrastructure.llm.qa_dataset_llm_gateway.QADatasetLlmGateway`
    via :class:`~src.services.qa_dataset_generation_service.QADatasetGenerationService`.
    """

    def __init__(
        self,
        *,
        qa_dataset: QADatasetEntriesPort,
        qa_dataset_generation_service: QADatasetGenerationService,
    ) -> None:
        self._qa = qa_dataset
        self._gen = qa_dataset_generation_service

    def execute(self, command: GenerateQaDatasetCommand) -> dict:
        normalized_mode = (command.generation_mode or "append").strip().lower()
        if normalized_mode not in {"append", "replace", "append_dedup"}:
            raise ValueError("generation_mode must be one of: append, replace, append_dedup.")

        deleted_existing_entries = 0

        if normalized_mode == "replace":
            deleted_existing_entries = DeleteAllQaDatasetEntriesUseCase(
                qa_dataset_service=self._qa
            ).execute(
                user_id=command.user_id,
                project_id=command.project_id,
            )

        existing_question_keys: set[str] = set()
        if normalized_mode == "append_dedup":
            existing_question_keys = self._qa.existing_question_keys(
                user_id=command.user_id,
                project_id=command.project_id,
            )

        generated_entries = self._gen.generate_entries(
            user_id=command.user_id,
            project_id=command.project_id,
            num_questions=command.num_questions,
            source_files=command.source_files,
        )

        create_uc = CreateQaDatasetEntryUseCase(qa_dataset=self._qa)
        created_entries = []
        skipped_duplicates = []

        for item in generated_entries:
            question = item["question"]
            question_key = normalized_qa_question_key(question)

            if normalized_mode == "append_dedup" and question_key in existing_question_keys:
                skipped_duplicates.append(question)
                continue

            created_entry = create_uc.execute(
                user_id=command.user_id,
                project_id=command.project_id,
                question=question,
                expected_answer=item.get("expected_answer"),
                expected_doc_ids=item.get("expected_doc_ids", []),
                expected_sources=item.get("expected_sources", []),
            )
            created_entries.append(created_entry)

            if normalized_mode == "append_dedup":
                existing_question_keys.add(question_key)

        return {
            "generation_mode": normalized_mode,
            "deleted_existing_entries": deleted_existing_entries,
            "created_entries": created_entries,
            "skipped_duplicates": skipped_duplicates,
            "requested_questions": int(command.num_questions),
            "raw_generated_count": len(generated_entries),
        }
