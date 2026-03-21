from src.domain.manual_evaluation_result import ManualEvaluationResult, is_manual_evaluation_result_like
from src.services.manual_evaluation_service import (
    build_expectation_comparison,
    detect_manual_evaluation_issues,
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


def test_detect_issues_no_answer_no_pipeline():
    issues = detect_manual_evaluation_issues(
        answer_stripped="",
        has_pipeline=False,
        confidence=0.0,
        groundedness=None,
        answer_relevance=None,
        hallucination_score=None,
        has_hallucination=None,
        doc_id_recall=None,
        source_recall=None,
        prompt_source_recall=None,
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
        doc_id_recall=None,
        source_recall=None,
        prompt_source_recall=None,
        expected_doc_ids=[],
        expected_sources=[],
        expected_answer=None,
    )
    assert issues == ["Hallucination detected"]


def test_detect_issues_low_doc_recall():
    issues = detect_manual_evaluation_issues(
        answer_stripped="ok",
        has_pipeline=True,
        confidence=0.9,
        groundedness=0.9,
        answer_relevance=0.9,
        hallucination_score=0.9,
        has_hallucination=False,
        doc_id_recall=0.0,
        source_recall=None,
        prompt_source_recall=None,
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
        doc_id_recall=None,
        source_recall=None,
        prompt_source_recall=None,
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
