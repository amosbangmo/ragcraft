import unittest

from src.domain.llm_judge_result import LLMJudgeResult
from src.domain.pipeline_payloads import PipelineBuildResult
from src.domain.qa_dataset_entry import QADatasetEntry
from src.services.evaluation_service import (
    EvaluationService,
    _latency_stage_row_fields,
    _mean_round,
    _r2,
    _rate,
)
from src.services.llm_judge_service import LLMJudgeService


class _StubJudge:
    def __init__(self, result: LLMJudgeResult) -> None:
        self._result = result

    def evaluate(self, **_kwargs) -> LLMJudgeResult:
        return self._result


class _StubSemanticSimilarity:
    def compute_similarity(self, answer: str, expected_answer: str) -> float:
        return 0.88 if (answer or "").strip() and (expected_answer or "").strip() else 0.0


class TestEvaluationServiceModuleHelpers(unittest.TestCase):
    def test_latency_stage_row_fields_empty(self) -> None:
        self.assertEqual(
            _latency_stage_row_fields(None),
            {
                "query_rewrite_ms": 0.0,
                "retrieval_ms": 0.0,
                "reranking_ms": 0.0,
                "prompt_build_ms": 0.0,
                "answer_generation_ms": 0.0,
            },
        )

    def test_latency_stage_row_fields_rounds(self) -> None:
        out = _latency_stage_row_fields(
            {
                "query_rewrite_ms": 1.234,
                "retrieval_ms": 2.0,
                "reranking_ms": 0.0,
                "prompt_build_ms": 3.456,
                "answer_generation_ms": 4.5,
            }
        )
        self.assertEqual(out["query_rewrite_ms"], 1.23)
        self.assertEqual(out["prompt_build_ms"], 3.46)

    def test_r2_none(self) -> None:
        self.assertIsNone(_r2(None))

    def test_r2_rounds(self) -> None:
        self.assertEqual(_r2(0.123456), 0.12)

    def test_mean_round_empty(self) -> None:
        self.assertIsNone(_mean_round([], 2))

    def test_mean_round(self) -> None:
        self.assertEqual(_mean_round([1.0, 2.0], 1), 1.5)

    def test_rate_zero_denominator(self) -> None:
        self.assertIsNone(_rate(1, 0))

    def test_rate(self) -> None:
        self.assertEqual(_rate(1, 4), 0.25)


class TestEvaluationServiceMetrics(unittest.TestCase):
    def setUp(self) -> None:
        self.ev = EvaluationService.__new__(EvaluationService)

    def test_precision_at_k_empty_ranked(self) -> None:
        self.assertEqual(
            self.ev._compute_precision_at_k(
                ranked_doc_ids=[],
                expected_doc_ids={"a"},
            ),
            0.0,
        )

    def test_precision_at_k(self) -> None:
        p = self.ev._compute_precision_at_k(
            ranked_doc_ids=["a", "b", "c"],
            expected_doc_ids={"a", "c"},
        )
        self.assertAlmostEqual(p, 2 / 3, places=5)

    def test_reciprocal_rank(self) -> None:
        self.assertEqual(
            self.ev._compute_reciprocal_rank(
                ranked_doc_ids=["x", "a"],
                expected_doc_ids={"a"},
            ),
            0.5,
        )
        self.assertEqual(
            self.ev._compute_reciprocal_rank(
                ranked_doc_ids=["b"],
                expected_doc_ids={"a"},
            ),
            0.0,
        )

    def test_average_precision(self) -> None:
        ap = self.ev._compute_average_precision(
            ranked_doc_ids=["a", "b", "c"],
            expected_doc_ids={"a", "c"},
        )
        self.assertAlmostEqual(ap, (1.0 + 2.0 / 3) / 2, places=5)

    def test_set_precision_recall_f1_empty_expected(self) -> None:
        p, r, f = self.ev._compute_set_precision_recall_f1(
            predicted_values={"a"},
            expected_values=set(),
        )
        self.assertEqual((p, r, f), (0.0, 0.0, 0.0))

    def test_set_precision_recall_f1(self) -> None:
        p, r, f = self.ev._compute_set_precision_recall_f1(
            predicted_values={"a", "b"},
            expected_values={"a", "c"},
        )
        self.assertAlmostEqual(p, 0.5)
        self.assertAlmostEqual(r, 0.5)
        self.assertAlmostEqual(f, 0.5)

    def test_answer_token_f1_exact_match(self) -> None:
        p, r, f = self.ev._compute_answer_precision_recall_f1(
            generated_answer="hello world",
            expected_answer="hello world",
        )
        self.assertEqual(p, 1.0)
        self.assertEqual(r, 1.0)
        self.assertEqual(f, 1.0)

    def test_answer_token_f1_no_overlap(self) -> None:
        p, r, f = self.ev._compute_answer_precision_recall_f1(
            generated_answer="foo",
            expected_answer="bar",
        )
        self.assertEqual((p, r, f), (0.0, 0.0, 0.0))

    def test_normalize_and_tokenize(self) -> None:
        self.assertEqual(
            self.ev._normalize_text("  Hello,\nWorld!!  "),
            "hello world",
        )
        self.assertEqual(
            self.ev._tokenize_text("a b  a"),
            ["a", "b", "a"],
        )
        self.assertEqual(self.ev._tokenize_text("   "), [])


class TestEvaluateGoldQADataset(unittest.TestCase):
    def test_pipeline_failure_row(self) -> None:
        entry = QADatasetEntry(
            id=7,
            user_id="u",
            project_id="p",
            question="q?",
            expected_answer="gold",
            expected_doc_ids=["d1"],
            expected_sources=["/a.pdf"],
        )

        def runner(_e: QADatasetEntry):
            return {
                "pipeline": None,
                "answer": "",
                "latency_ms": 12.34,
            }

        judge = LLMJudgeResult(
            groundedness_score=0.0,
            citation_faithfulness_score=0.0,
            answer_relevance_score=0.0,
            hallucination_score=0.0,
            has_hallucination=False,
            reason=None,
        )
        result = EvaluationService(
            llm_judge_service=_StubJudge(judge),
        ).evaluate_gold_qa_dataset(entries=[entry], pipeline_runner=runner)

        self.assertEqual(result.summary.data.get("successful_queries"), 0)
        self.assertEqual(result.summary.data.get("total_entries"), 1)
        row = result.rows[0].data
        self.assertTrue(row.get("pipeline_failed"))
        self.assertIs(row.get("judge_failed"), False)
        self.assertEqual(row.get("retrieval_mode"), "none")
        self.assertIsNone(row.get("recall_at_k"))
        self.assertEqual(row.get("latency_ms"), 12.3)
        self.assertIn("failure_labels", row)

    def test_pipeline_build_result_dict_path(self) -> None:
        entry = QADatasetEntry(
            id=1,
            user_id="u",
            project_id="p",
            question="What?",
            expected_answer="the answer",
            expected_doc_ids=["doc-a"],
            expected_sources=[],
        )
        pl = PipelineBuildResult(
            selected_doc_ids=["doc-a", "doc-b"],
            prompt_sources=[
                {"source_number": 1, "doc_id": "doc-a", "source_file": "a.pdf"},
            ],
            raw_context="ctx",
            confidence=0.9,
            retrieval_mode="hybrid",
            query_rewrite_enabled=True,
            hybrid_retrieval_enabled=True,
            latency={"retrieval_ms": 5.555},
        )

        def runner(_e: QADatasetEntry):
            return {
                "pipeline": pl,
                "answer": "the answer",
                "latency_ms": 100.0,
            }

        judge = LLMJudgeResult(
            groundedness_score=0.9,
            citation_faithfulness_score=0.8,
            answer_relevance_score=0.85,
            hallucination_score=0.1,
            has_hallucination=False,
            answer_correctness_score=0.95,
            reason=None,
        )
        result = EvaluationService(
            llm_judge_service=_StubJudge(judge),
            semantic_similarity_service=_StubSemanticSimilarity(),
        ).evaluate_gold_qa_dataset(entries=[entry], pipeline_runner=runner)

        self.assertEqual(result.summary.data.get("successful_queries"), 1)
        row = result.rows[0].data
        self.assertFalse(row.get("pipeline_failed"))
        self.assertIs(row.get("judge_failed"), False)
        self.assertEqual(row.get("recall_at_k"), 1.0)
        self.assertEqual(row.get("hit_at_k"), 1.0)
        self.assertEqual(row.get("answer_f1"), 1.0)
        self.assertEqual(row.get("semantic_similarity"), 0.88)
        self.assertEqual(row.get("retrieval_mode"), "hybrid")
        self.assertTrue(row.get("query_rewrite_enabled"))
        self.assertTrue(row.get("hybrid_retrieval_enabled"))
        self.assertEqual(row.get("retrieval_ms"), round(5.555, 2))
        self.assertEqual(row.get("answer_correctness_score"), 0.95)
        self.assertIsNotNone(result.summary.data.get("avg_answer_f1"))
        self.assertIsInstance(result.correlations, dict)

    def test_judge_failure_row_flagged_and_excluded_from_judge_aggregates(self) -> None:
        good = LLMJudgeResult(
            groundedness_score=0.8,
            citation_faithfulness_score=0.8,
            answer_relevance_score=0.8,
            hallucination_score=0.9,
            has_hallucination=False,
            answer_correctness_score=0.85,
            reason=None,
        )
        bad = LLMJudgeService._failure_result()

        class _SwitchJudge:
            def __init__(self) -> None:
                self._n = 0

            def evaluate(self, **_kwargs) -> LLMJudgeResult:
                self._n += 1
                return bad if self._n == 1 else good

        def _entry(eid: int) -> QADatasetEntry:
            return QADatasetEntry(
                id=eid,
                user_id="u",
                project_id="p",
                question="Q?",
                expected_answer="gold",
                expected_doc_ids=["d1"],
                expected_sources=[],
            )

        def runner(_e: QADatasetEntry):
            return {
                "pipeline": PipelineBuildResult(
                    selected_doc_ids=["d1"],
                    prompt_sources=[
                        {"source_number": 1, "doc_id": "d1", "source_file": "a.pdf"},
                    ],
                    raw_context="ctx",
                    confidence=0.5,
                    retrieval_mode="faiss",
                    query_rewrite_enabled=False,
                    hybrid_retrieval_enabled=False,
                ),
                "answer": "gold",
                "latency_ms": 1.0,
            }

        result = EvaluationService(
            llm_judge_service=_SwitchJudge(),
            semantic_similarity_service=_StubSemanticSimilarity(),
        ).evaluate_gold_qa_dataset(
            entries=[_entry(1), _entry(2)],
            pipeline_runner=runner,
        )
        r0, r1 = result.rows[0].data, result.rows[1].data
        self.assertTrue(r0.get("judge_failed"))
        self.assertFalse(r1.get("judge_failed"))
        self.assertIsNone(r0.get("groundedness_score"))
        self.assertIsNone(r0.get("hallucination_score"))
        self.assertIsNone(r0.get("has_hallucination"))
        self.assertEqual(r0.get("judge_failure_reason"), "judge_failure")
        summ = result.summary.data
        self.assertEqual(summ.get("avg_groundedness_score"), 0.8)
        self.assertEqual(summ.get("avg_hallucination_score"), 0.9)
        self.assertEqual(summ.get("avg_answer_correctness"), 0.85)
        self.assertEqual(summ.get("hallucination_rate"), 0.0)
        self.assertIn("judge_failure", r0.get("failure_labels", []))
        self.assertNotIn("hallucination", r0.get("failure_labels", []))


if __name__ == "__main__":
    unittest.main()
