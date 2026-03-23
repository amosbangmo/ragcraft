from unittest.mock import MagicMock

from application.dto.evaluation import RunManualEvaluationCommand
from application.use_cases.evaluation.run_manual_evaluation import RunManualEvaluationUseCase
from domain.evaluation.benchmark_result import BenchmarkResult, BenchmarkRow, BenchmarkSummary
from domain.evaluation.manual_evaluation_result import (
    ManualEvaluationResult,
    is_manual_evaluation_result_like,
)
from domain.rag.pipeline_latency import PipelineLatency
from domain.rag.pipeline_payloads import PipelineBuildResult
from domain.projects.project import Project
from infrastructure.evaluation.evaluation_service import EvaluationService
from infrastructure.evaluation.llm_judge_service import JUDGE_FAILURE_REASON
from infrastructure.evaluation.manual_evaluation_service import (
    _ordered_sources_from_pipeline,
    _row_optional_float,
    _row_optional_int,
    build_expectation_comparison,
    detect_manual_evaluation_issues,
)


def _run_manual_evaluation_uc(
    *,
    user_id: str,
    project_id: str,
    inspect_return,
    generate_answer: str | None,
    benchmark: BenchmarkResult,
) -> RunManualEvaluationUseCase:
    project = Project(user_id=user_id, project_id=project_id)
    project_service = MagicMock()
    project_service.get_project.return_value = project
    inspect = MagicMock()
    inspect.execute.return_value = inspect_return
    generate = MagicMock()
    if generate_answer is not None:
        generate.execute.return_value = generate_answer
    gold = MagicMock()
    gold.evaluate_gold_qa_dataset.return_value = benchmark
    return RunManualEvaluationUseCase(
        project_service=project_service,
        inspect_pipeline=inspect,
        generate_answer_from_pipeline=generate,
        manual_evaluation=EvaluationService(gold_qa_benchmark=gold),
    )


def test_build_expectation_comparison_matched_and_missing():
    comp = build_expectation_comparison(
        expected_doc_ids=["a", "b"],
        expected_sources=["x.pdf", "y.pdf"],
        retrieved_doc_ids=["b", "c"],
        retrieved_sources=["y.pdf"],
    )
    assert comp.matched_doc_ids == ["b"]
    assert comp.missing_doc_ids == ["a"]
    assert comp.matched_sources == ["y.pdf"]
    assert comp.missing_sources == ["x.pdf"]
    assert comp.retrieved_doc_ids == ["b", "c"]
    assert comp.expected_doc_ids == ["a", "b"]


def test_row_optional_float_and_int():
    assert _row_optional_float({"x": None}, "x") is None
    assert _row_optional_float({"x": 0.25}, "x") == 0.25
    assert _row_optional_float({"x": "bad"}, "x") is None
    assert _row_optional_int({"n": 3}, "n") == 3
    assert _row_optional_int({"n": None}, "n") is None


def test_detect_issues_pipeline_failed_skips_no_answer_message():
    issues = detect_manual_evaluation_issues(
        answer_stripped="",
        has_pipeline=False,
        confidence=0.0,
        groundedness=None,
        answer_relevance=None,
        hallucination_score=None,
        has_hallucination=None,
        recall_at_k=None,
        source_recall=None,
        prompt_doc_id_recall=None,
        citation_doc_id_recall=None,
        expected_doc_ids=[],
        expected_sources=[],
        expected_answer=None,
        pipeline_failed=True,
    )
    assert "No answer generated" not in issues


def test_detect_issues_no_answer_no_pipeline():
    issues = detect_manual_evaluation_issues(
        answer_stripped="",
        has_pipeline=False,
        confidence=0.0,
        groundedness=None,
        answer_relevance=None,
        hallucination_score=None,
        has_hallucination=None,
        recall_at_k=None,
        source_recall=None,
        prompt_doc_id_recall=None,
        citation_doc_id_recall=None,
        expected_doc_ids=[],
        expected_sources=[],
        expected_answer=None,
    )
    assert "No answer generated" in issues
    assert "Low confidence" in issues


def test_detect_issues_hallucination_flag():
    issues = detect_manual_evaluation_issues(
        answer_stripped="hello",
        has_pipeline=True,
        confidence=0.9,
        groundedness=0.9,
        answer_relevance=0.9,
        hallucination_score=0.9,
        has_hallucination=True,
        recall_at_k=None,
        source_recall=None,
        prompt_doc_id_recall=None,
        citation_doc_id_recall=None,
        expected_doc_ids=[],
        expected_sources=[],
        expected_answer=None,
    )
    assert issues == ["Hallucination detected"]


def test_detect_issues_low_citation_recall():
    issues = detect_manual_evaluation_issues(
        answer_stripped="ok",
        has_pipeline=True,
        confidence=0.9,
        groundedness=0.9,
        answer_relevance=0.9,
        hallucination_score=0.9,
        has_hallucination=False,
        recall_at_k=1.0,
        source_recall=None,
        prompt_doc_id_recall=1.0,
        citation_doc_id_recall=0.0,
        expected_doc_ids=["d1"],
        expected_sources=[],
        expected_answer=None,
    )
    assert "Low answer citation recall (expected doc IDs)" in issues


def test_detect_issues_low_doc_recall():
    issues = detect_manual_evaluation_issues(
        answer_stripped="ok",
        has_pipeline=True,
        confidence=0.9,
        groundedness=0.9,
        answer_relevance=0.9,
        hallucination_score=0.9,
        has_hallucination=False,
        recall_at_k=0.0,
        source_recall=None,
        prompt_doc_id_recall=None,
        citation_doc_id_recall=None,
        expected_doc_ids=["d1"],
        expected_sources=[],
        expected_answer=None,
    )
    assert "No expected document retrieved" in issues


def test_detect_issues_dedupes_duplicate_messages():
    issues = detect_manual_evaluation_issues(
        answer_stripped="",
        has_pipeline=False,
        confidence=0.0,
        groundedness=None,
        answer_relevance=None,
        hallucination_score=None,
        has_hallucination=None,
        recall_at_k=None,
        source_recall=None,
        prompt_doc_id_recall=None,
        citation_doc_id_recall=None,
        expected_doc_ids=[],
        expected_sources=[],
        expected_answer="gold",
    )
    assert issues.count("No answer generated") == 1


def test_is_manual_evaluation_result_like_domain_instance():
    r = ManualEvaluationResult(
        question="q",
        answer="a",
        expected_answer=None,
        confidence=0.5,
    )
    assert is_manual_evaluation_result_like(r) is True


def test_is_manual_evaluation_result_like_duplicate_named_class():
    """Simulates Streamlit reload: same class name, different object identity."""

    class ManualEvaluationResult:  # noqa: PLW1641 — intentional shadow for test
        def __init__(self) -> None:
            self.answer = "x"
            self.question = "y"
            self.confidence = 0.3

    dup = ManualEvaluationResult()
    assert is_manual_evaluation_result_like(dup) is True


def test_is_manual_evaluation_result_like_rejects_garbage():
    assert is_manual_evaluation_result_like(None) is False
    assert is_manual_evaluation_result_like({}) is False
    assert is_manual_evaluation_result_like("x") is False


def test_ordered_sources_from_pipeline_variants():
    assert _ordered_sources_from_pipeline(None) == []
    assert _ordered_sources_from_pipeline({}) == []
    assert _ordered_sources_from_pipeline({"prompt_sources": "bad"}) == []
    assert _ordered_sources_from_pipeline(
        {
            "prompt_sources": [
                {"source_file": "a.pdf"},
                "skip",
                {"source_file": "a.pdf"},
                {"nope": 1},
            ]
        }
    ) == ["a.pdf"]
    pl = PipelineBuildResult(
        prompt_sources=[{"source_file": "b.pdf"}, {"source_file": "c.pdf"}]
    )
    assert _ordered_sources_from_pipeline(pl) == ["b.pdf", "c.pdf"]


def test_run_manual_evaluation_without_pipeline():
    bench = BenchmarkResult(
        summary=BenchmarkSummary(data={}),
        rows=[
            BenchmarkRow(
                entry_id=0,
                question="Q",
                data={
                    "pipeline_failed": False,
                    "judge_failed": False,
                    "confidence": 0.4,
                },
            )
        ],
    )
    uc = _run_manual_evaluation_uc(
        user_id="u1",
        project_id="p1",
        inspect_return=None,
        generate_answer=None,
        benchmark=bench,
    )
    r = uc.execute(
        RunManualEvaluationCommand(user_id="u1", project_id="p1", question="  What?  ")
    )
    assert r.question == "What?"
    assert r.answer_citation_quality is None


def test_run_manual_evaluation_with_pipeline_and_judge_branches():
    pipeline = PipelineBuildResult(
        prompt_sources=[{"source_file": "a.pdf"}, "x", {"source_file": "a.pdf"}],
        selected_doc_ids=["d1", ""],
        reranked_raw_assets=[{"k": 1}, "bad"],
        latency=PipelineLatency(query_rewrite_ms=1.0, retrieval_ms=2.0),
    )
    bench = BenchmarkResult(
        summary=BenchmarkSummary(data={}),
        rows=[
            BenchmarkRow(
                entry_id=0,
                question="Q",
                data={
                    "pipeline_failed": False,
                    "judge_failed": True,
                    "judge_failure_reason": "rate limited",
                    "confidence": 0.9,
                    "retrieval_mode": "hybrid",
                    "query_rewrite_enabled": True,
                    "hybrid_retrieval_enabled": True,
                    "latency_ms": 12.0,
                    "citation_doc_id_precision": 0.1,
                    "citation_doc_id_recall": 0.2,
                    "citation_doc_id_f1": 0.3,
                    "citation_doc_id_overlap_count": 1,
                    "citation_doc_ids_count": 2,
                    "retrieved_doc_ids_count": 3,
                    "retrieved_sources_count": 1,
                },
            )
        ],
    )
    uc = _run_manual_evaluation_uc(
        user_id="u1",
        project_id="p1",
        inspect_return=pipeline,
        generate_answer="  ans  ",
        benchmark=bench,
    )
    r = uc.execute(
        RunManualEvaluationCommand(
            user_id="u1",
            project_id="p1",
            question="Q",
            expected_doc_ids=["d1"],
            expected_sources=["a.pdf"],
            expected_answer="gold",
        )
    )
    assert "rate limited" in " ".join(r.detected_issues)
    assert r.expectation_comparison is not None
    assert r.answer_citation_quality is not None


def test_run_manual_evaluation_judge_failure_default_message():
    bench = BenchmarkResult(
        summary=BenchmarkSummary(data={}),
        rows=[
            BenchmarkRow(
                entry_id=0,
                question="Q",
                data={
                    "judge_failed": True,
                    "judge_failure_reason": JUDGE_FAILURE_REASON,
                    "confidence": 0.5,
                    "pipeline_failed": False,
                },
            )
        ],
    )
    uc = _run_manual_evaluation_uc(
        user_id="u",
        project_id="p",
        inspect_return=PipelineBuildResult(),
        generate_answer="ok",
        benchmark=bench,
    )
    r = uc.execute(RunManualEvaluationCommand(user_id="u", project_id="p", question="Q"))
    assert any("LLM judge could not score" in i for i in r.detected_issues)
    assert not any("rate limited" in i for i in r.detected_issues)


def test_run_manual_evaluation_pipeline_failed_banner():
    bench = BenchmarkResult(
        summary=BenchmarkSummary(data={}),
        rows=[
            BenchmarkRow(
                entry_id=0,
                question="Q",
                data={
                    "pipeline_failed": True,
                    "judge_failed": False,
                    "confidence": 0.0,
                },
            )
        ],
    )
    uc = _run_manual_evaluation_uc(
        user_id="u",
        project_id="p",
        inspect_return=PipelineBuildResult(),
        generate_answer="",
        benchmark=bench,
    )
    r = uc.execute(RunManualEvaluationCommand(user_id="u", project_id="p", question="Q"))
    assert any("pipeline" in i.lower() for i in r.detected_issues)
