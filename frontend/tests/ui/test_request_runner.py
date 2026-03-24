from __future__ import annotations

import contextlib
import unittest
from unittest.mock import MagicMock, patch

from components.shared import request_runner as rr
from services.contract.evaluation_wire_models import BenchmarkResult, BenchmarkRow, BenchmarkSummary


class _RerunStub(Exception):
    """Mirrors Streamlit stopping the script when ``st.rerun()`` is invoked."""


class TestAnalyzeDatasetEvaluationSession(unittest.TestCase):
    def test_analyze_missing_and_runner_error(self) -> None:
        v = rr.analyze_dataset_evaluation_session_payload(None)
        self.assertEqual(v.kind, "missing")
        v2 = rr.analyze_dataset_evaluation_session_payload({rr.RUNNER_ERROR_KEY: "boom"})
        self.assertEqual(v2.kind, "runner_error")
        self.assertEqual(v2.runner_error_message, "boom")

    def test_analyze_invalid_shape_and_invalid_result(self) -> None:
        v = rr.analyze_dataset_evaluation_session_payload({"foo": 1})
        self.assertEqual(v.kind, "invalid_shape")
        v2 = rr.analyze_dataset_evaluation_session_payload({"result": "nope"})
        self.assertEqual(v2.kind, "invalid_result")

    def test_analyze_ok_matches_read_helper(self) -> None:
        bench = BenchmarkResult(
            summary=BenchmarkSummary(data={"avg_recall_at_k": 0.5}),
            rows=[BenchmarkRow(entry_id=1, question="q", data={})],
        )
        raw = {"result": bench, "enable_query_rewrite": True}
        v = rr.analyze_dataset_evaluation_session_payload(raw)
        self.assertEqual(v.kind, "ok")
        self.assertIsNotNone(v.result)
        parsed = rr.read_dataset_evaluation_session_payload(raw)
        self.assertIsNotNone(parsed)


class TestRunnerPayloadHelpers(unittest.TestCase):
    def test_is_runner_error_payload(self) -> None:
        self.assertFalse(rr.is_runner_error_payload(None))
        self.assertFalse(rr.is_runner_error_payload("x"))
        self.assertFalse(rr.is_runner_error_payload({"ok": True}))
        self.assertTrue(rr.is_runner_error_payload({rr.RUNNER_ERROR_KEY: "failed"}))

    def test_read_dataset_evaluation_session_payload_none_and_errors(self) -> None:
        self.assertIsNone(rr.read_dataset_evaluation_session_payload(None))
        self.assertIsNone(rr.read_dataset_evaluation_session_payload({rr.RUNNER_ERROR_KEY: "x"}))
        self.assertIsNone(rr.read_dataset_evaluation_session_payload({"foo": 1}))
        self.assertIsNone(rr.read_dataset_evaluation_session_payload({"result": "not-coercible"}))

    def test_read_dataset_evaluation_session_payload_success(self) -> None:
        bench = BenchmarkResult(
            summary=BenchmarkSummary(data={"avg_recall_at_k": 0.5}),
            rows=[BenchmarkRow(entry_id=1, question="q", data={})],
        )
        raw = {
            "result": bench,
            "enable_query_rewrite": True,
            "enable_hybrid_retrieval": False,
            "generated_at": "2025-01-01T00:00:00Z",
        }
        parsed = rr.read_dataset_evaluation_session_payload(raw)
        self.assertIsNotNone(parsed)
        assert parsed is not None
        got_bench, meta = parsed
        # Avoid ``isinstance`` against a second imported ``BenchmarkResult`` class when the
        # full suite loads both wire and domain modules in different orders.
        self.assertEqual(type(got_bench).__name__, "BenchmarkResult")
        self.assertEqual(got_bench.rows[0].entry_id, 1)
        self.assertTrue(meta.get("enable_query_rewrite"))
        self.assertFalse(meta.get("enable_hybrid_retrieval"))
        self.assertEqual(meta.get("generated_at"), "2025-01-01T00:00:00Z")


class TestRunRequestAction(unittest.TestCase):
    def setUp(self) -> None:
        self.session: dict[str, object] = {}

    @staticmethod
    @contextlib.contextmanager
    def _fake_spinner(_text: str):
        yield None

    def _run_with_streamlit_mocks(self, *, rerun_mock: MagicMock):
        return patch.multiple(
            rr.st,
            session_state=self.session,
            spinner=self._fake_spinner,
            rerun=rerun_mock,
        )

    def test_trigger_clears_result_and_sets_running_then_reruns(self) -> None:
        self.session["rq"] = False
        self.session["rs"] = {"old": True}
        rerun_mock = MagicMock(side_effect=_RerunStub)
        with self._run_with_streamlit_mocks(rerun_mock=rerun_mock):
            with self.assertRaises(_RerunStub):
                rr.run_request_action(
                    request_key="rq",
                    result_key="rs",
                    trigger=True,
                    can_run=True,
                    action=lambda: None,
                    spinner_text="…",
                    error_mapper=lambda e: str(e),
                )
        self.assertIsNone(self.session.get("rs"))
        self.assertTrue(bool(self.session.get("rq")))
        rerun_mock.assert_called_once()

    def test_can_run_false_leaves_session(self) -> None:
        self.session["rq"] = False
        self.session["rs"] = {"keep": 1}
        rerun_mock = MagicMock()
        with self._run_with_streamlit_mocks(rerun_mock=rerun_mock):
            rr.run_request_action(
                request_key="rq",
                result_key="rs",
                trigger=True,
                can_run=False,
                action=lambda: 1 / 0,
                spinner_text="…",
                error_mapper=lambda e: str(e),
            )
        self.assertEqual(self.session.get("rs"), {"keep": 1})
        self.assertFalse(bool(self.session.get("rq")))
        rerun_mock.assert_not_called()

    def test_executing_phase_stores_result_and_finishes(self) -> None:
        self.session["rq"] = True
        self.session["rs"] = None
        calls: list[int] = []

        def action():
            calls.append(1)
            return {"ok": True}

        rerun_mock = MagicMock(side_effect=_RerunStub)
        with self._run_with_streamlit_mocks(rerun_mock=rerun_mock):
            with self.assertRaises(_RerunStub):
                rr.run_request_action(
                    request_key="rq",
                    result_key="rs",
                    trigger=False,
                    can_run=True,
                    action=action,
                    spinner_text="…",
                    error_mapper=lambda e: str(e),
                )
        self.assertEqual(calls, [1])
        self.assertEqual(self.session.get("rs"), {"ok": True})
        self.assertFalse(bool(self.session.get("rq")))
        self.assertEqual(rerun_mock.call_count, 1)

    def test_error_mapper_exception_falls_back_to_str(self) -> None:
        self.session["rq"] = True
        self.session["rs"] = None

        def action():
            raise ValueError("boom")

        def bad_mapper(_exc: Exception) -> str:
            raise RuntimeError("mapper broke")

        rerun_mock = MagicMock(side_effect=_RerunStub)
        with self._run_with_streamlit_mocks(rerun_mock=rerun_mock):
            with self.assertRaises(_RerunStub):
                rr.run_request_action(
                    request_key="rq",
                    result_key="rs",
                    trigger=False,
                    can_run=True,
                    action=action,
                    spinner_text="…",
                    error_mapper=bad_mapper,
                )
        err = self.session.get("rs")
        self.assertIsInstance(err, dict)
        self.assertIn(rr.RUNNER_ERROR_KEY, err)
        self.assertEqual(err[rr.RUNNER_ERROR_KEY], "boom")
        self.assertFalse(bool(self.session.get("rq")))


if __name__ == "__main__":
    unittest.main()
