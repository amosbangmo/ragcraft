from __future__ import annotations

from unittest.mock import MagicMock

from src.application.evaluation.dtos import GenerateQaDatasetCommand, GenerateQaDatasetResult
from src.application.use_cases.evaluation.generate_qa_dataset import GenerateQaDatasetUseCase
from src.domain.qa_dataset_entry import QADatasetEntry
from src.domain.qa_dataset_proposal import ProposedQaDatasetRow


def test_generate_qa_dataset_returns_typed_result() -> None:
    gen = MagicMock()
    gen.generate_entries.return_value = [
        ProposedQaDatasetRow(
            question="Q1?",
            expected_answer="A1",
            expected_doc_ids=("d1",),
            expected_sources=("f1.pdf",),
        )
    ]

    qa_port = MagicMock()

    def _create_entry(**kwargs):  # noqa: ANN003
        return QADatasetEntry(
            id=99,
            user_id=kwargs["user_id"],
            project_id=kwargs["project_id"],
            question=kwargs["question"],
            expected_answer=kwargs.get("expected_answer"),
            expected_doc_ids=list(kwargs.get("expected_doc_ids") or []),
            expected_sources=list(kwargs.get("expected_sources") or []),
        )

    qa_port.create_entry.side_effect = _create_entry

    uc = GenerateQaDatasetUseCase(qa_dataset=qa_port, qa_dataset_generation_service=gen)
    out = uc.execute(
        GenerateQaDatasetCommand(
            user_id="u",
            project_id="p",
            num_questions=3,
            generation_mode="append",
        )
    )

    assert isinstance(out, GenerateQaDatasetResult)
    assert out.generation_mode == "append"
    assert out.raw_generated_count == 1
    assert len(out.created_entries) == 1
    assert out.created_entries[0].question == "Q1?"
