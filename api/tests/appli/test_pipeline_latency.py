import unittest

from domain.rag.pipeline_latency import PipelineLatency, merge_with_answer_stage


class TestPipelineLatency(unittest.TestCase):
    def test_to_dict_round_trip(self):
        p = PipelineLatency(
            query_rewrite_ms=1.0,
            retrieval_ms=2.0,
            reranking_ms=3.0,
            prompt_build_ms=4.0,
            answer_generation_ms=5.0,
            total_ms=15.0,
        )
        d = p.to_dict()
        self.assertEqual(set(d.keys()), set(PipelineLatency().to_dict().keys()))
        restored = PipelineLatency.from_dict(d)
        self.assertEqual(restored, p)

    def test_from_dict_empty(self):
        self.assertEqual(PipelineLatency.from_dict(None), PipelineLatency())
        self.assertEqual(PipelineLatency.from_dict({}), PipelineLatency())

    def test_merge_with_answer_stage(self):
        partial = PipelineLatency(
            query_rewrite_ms=1.0,
            retrieval_ms=2.0,
            reranking_ms=3.0,
            prompt_build_ms=4.0,
            answer_generation_ms=0.0,
            total_ms=10.0,
        )
        merged = merge_with_answer_stage(
            partial,
            answer_generation_ms=7.0,
            total_ms=20.0,
        )
        self.assertEqual(merged.answer_generation_ms, 7.0)
        self.assertEqual(merged.total_ms, 20.0)
        self.assertEqual(merged.retrieval_ms, 2.0)
        for k, v in merged.to_dict().items():
            self.assertGreaterEqual(v, 0.0, msg=k)


if __name__ == "__main__":
    unittest.main()
