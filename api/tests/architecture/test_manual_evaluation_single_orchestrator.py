"""Guardrail: manual evaluation must not reintroduce a second orchestration entry point."""

from __future__ import annotations

import importlib


def test_manual_evaluation_module_exposes_no_manual_evaluation_service_class() -> None:
    mod = importlib.import_module(
        "infrastructure.evaluation.manual_evaluation_service",
    )
    assert not hasattr(mod, "ManualEvaluationService"), (
        "Use RunManualEvaluationUseCase + execute_rag_inspect_then_answer_for_evaluation only; "
        "do not add ManualEvaluationService.evaluate_question-style parallel orchestration."
    )


def test_run_manual_evaluation_use_case_module_importable() -> None:
    from application.use_cases.evaluation.run_manual_evaluation import (
        RunManualEvaluationUseCase,
    )

    assert RunManualEvaluationUseCase.__name__ == "RunManualEvaluationUseCase"
