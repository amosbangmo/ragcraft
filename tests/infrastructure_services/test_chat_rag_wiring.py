import os
import sys
import types
import unittest
from dataclasses import asdict, is_dataclass
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

os.environ.setdefault("OPENAI_API_KEY", "test-key")

if "langchain_core.documents" not in sys.modules:
    langchain_core_module = types.ModuleType("langchain_core")
    documents_module = types.ModuleType("langchain_core.documents")

    class Document:
        def __init__(self, page_content: str, metadata: dict | None = None):
            self.page_content = page_content
            self.metadata = metadata or {}

    documents_module.Document = Document
    langchain_core_module.documents = documents_module
    sys.modules["langchain_core"] = langchain_core_module
    sys.modules["langchain_core.documents"] = documents_module

if "src.core.config" not in sys.modules:
    sys.modules["src.core.config"] = types.ModuleType("src.core.config")

config_module = sys.modules["src.core.config"]
if not hasattr(config_module, "RetrievalConfig"):

    class RetrievalConfig:
        pass

    config_module.RetrievalConfig = RetrievalConfig

if not hasattr(config_module, "LLM"):
    config_module.LLM = SimpleNamespace(invoke=lambda prompt: SimpleNamespace(content="ok"))
if not hasattr(config_module, "RETRIEVAL_CONFIG"):
    config_module.RETRIEVAL_CONFIG = SimpleNamespace(
        query_rewrite_max_history_messages=6,
        max_text_chars_per_asset=4000,
        max_table_chars_per_asset=4000,
        enable_query_rewrite=True,
        enable_hybrid_retrieval=True,
        enable_contextual_compression=True,
        similarity_search_k=15,
        bm25_search_k=10,
        hybrid_search_k=10,
        bm25_k1=1.5,
        bm25_b=0.75,
        bm25_epsilon=0.25,
        rrf_k=60,
        hybrid_beta=0.5,
        max_prompt_assets=5,
        enable_section_expansion=True,
        section_expansion_neighbor_window=2,
        section_expansion_max_per_section=12,
        section_expansion_global_max=64,
    )

if "src.infrastructure.vectorstores.faiss.vector_store" not in sys.modules:
    faiss_store_module = types.ModuleType("src.infrastructure.vectorstores.faiss.vector_store")

    def _noop(*args, **kwargs):
        return None

    faiss_store_module.load_vector_store = _noop
    faiss_store_module.save_vector_store = _noop
    faiss_store_module.create_or_update_vector_store = _noop
    faiss_store_module.delete_documents_from_vector_store = _noop
    sys.modules["src.infrastructure.vectorstores.faiss.vector_store"] = faiss_store_module

from src.core.exceptions import LLMServiceError
from src.infrastructure.adapters.rag.retrieval_settings_service import RetrievalSettingsService
from src.domain.pipeline_payloads import ContextCompressionStats, PipelineBuildResult
from src.domain.project import Project
from src.domain.query_intent import QueryIntent
from src.domain.prompt_source import PromptSource
from src.domain.summary_recall_document import SummaryRecallDocument
from src.application.rag.dtos.recall_stages import VectorLexicalRecallBundle
from src.application.chat.policies.pipeline_document_selection import deduplicate_summary_doc_ids
from src.application.use_cases.chat.orchestration.summary_recall_ports import merge_summary_recall_documents
from src.composition.chat_rag_wiring import ChatRagUseCases, build_chat_rag_use_cases, build_rag_retrieval_subgraph
from src.infrastructure.adapters.rag.confidence_service import ConfidenceService


def _mutable_retrieval_config_view(cfg):
    if is_dataclass(cfg) and cfg.__dataclass_params__.frozen:
        return SimpleNamespace(**asdict(cfg))
    return cfg


class _ChatRagWiringHarness:
    """Holds :class:`RagRetrievalSubgraph` + :class:`ChatRagUseCases` the same way composition does (no RAG façade)."""

    def __init__(self, subgraph, use_cases: ChatRagUseCases, *, query_log_service):
        self.subgraph = subgraph
        self.use_cases = use_cases
        self.query_log_service = query_log_service

    @property
    def config(self):
        return self.subgraph.config

    @config.setter
    def config(self, value):
        self.subgraph.config = value

    @property
    def summary_recall_stage(self):
        return self.subgraph.summary_recall_stage

    @property
    def post_recall_stage_services(self):
        return self.subgraph.post_recall_stage_services

    @property
    def retrieval_settings_service(self):
        return self.subgraph.retrieval_settings_service


class TestChatRagWiringComposition(unittest.TestCase):
    def _build_harness(self, query_log_service=None):
        vectorstore_service = MagicMock()
        evaluation_service = MagicMock()
        docstore_service = MagicMock()
        reranking_service = MagicMock()
        retrieval_settings_service = RetrievalSettingsService()
        subgraph = build_rag_retrieval_subgraph(
            vectorstore_service=vectorstore_service,
            docstore_service=docstore_service,
            reranking_service=reranking_service,
            retrieval_settings_service=retrieval_settings_service,
        )
        ucs = build_chat_rag_use_cases(subgraph, query_log=query_log_service)
        harness = _ChatRagWiringHarness(subgraph, ucs, query_log_service=query_log_service)
        harness.config = _mutable_retrieval_config_view(harness.config)
        harness.config.hybrid_beta = 0.5
        harness.config.rrf_k = 60
        return (
            harness,
            vectorstore_service,
            evaluation_service,
            docstore_service,
            reranking_service,
        )

    def test_deduplicate_doc_ids_preserves_order(self):
        harness, *_ = self._build_harness()
        docs = [
            SummaryRecallDocument(page_content="a", metadata={"doc_id": "d1"}),
            SummaryRecallDocument(page_content="b", metadata={"doc_id": "d2"}),
            SummaryRecallDocument(page_content="c", metadata={"doc_id": "d1"}),
            SummaryRecallDocument(page_content="d", metadata={}),
        ]

        result = deduplicate_summary_doc_ids(docs)

        self.assertEqual(result, ["d1", "d2"])

    def test_rrf_merge_prioritizes_common_docs(self):
        harness, *_ = self._build_harness()
        harness.config.rrf_k = 60
        settings = harness.retrieval_settings_service.get_default()

        primary_docs = [
            SummaryRecallDocument(page_content="p1", metadata={"doc_id": "d1"}),
            SummaryRecallDocument(page_content="p2", metadata={"doc_id": "d2"}),
        ]
        secondary_docs = [
            SummaryRecallDocument(page_content="s1", metadata={"doc_id": "d2"}),
            SummaryRecallDocument(page_content="s2", metadata={"doc_id": "d3"}),
        ]

        merged = merge_summary_recall_documents(
            settings=settings,
            primary_docs=primary_docs,
            secondary_docs=secondary_docs,
        )
        merged_ids = [doc.metadata["doc_id"] for doc in merged]

        self.assertEqual(merged_ids[:2], ["d2", "d1"])

    def test_rrf_merge_respects_max_docs(self):
        harness, *_ = self._build_harness()
        harness.config.rrf_k = 60
        settings = harness.retrieval_settings_service.get_default()

        primary_docs = [
            SummaryRecallDocument(page_content="p1", metadata={"doc_id": "d1"}),
            SummaryRecallDocument(page_content="p2", metadata={"doc_id": "d2"}),
        ]
        secondary_docs = [
            SummaryRecallDocument(page_content="s1", metadata={"doc_id": "d2"}),
            SummaryRecallDocument(page_content="s2", metadata={"doc_id": "d3"}),
        ]

        merged = merge_summary_recall_documents(
            settings=settings,
            primary_docs=primary_docs,
            secondary_docs=secondary_docs,
            max_docs=2,
        )
        merged_ids = [doc.metadata["doc_id"] for doc in merged]
        self.assertEqual(merged_ids, ["d2", "d1"])

    def test_rrf_merge_beta_one_prioritizes_semantic_only_docs(self):
        harness, *_ = self._build_harness()
        harness.config.rrf_k = 60
        harness.config.hybrid_beta = 1.0
        settings = harness.retrieval_settings_service.get_default()

        primary_docs = [
            SummaryRecallDocument(page_content="p1", metadata={"doc_id": "d1"}),
            SummaryRecallDocument(page_content="p2", metadata={"doc_id": "d2"}),
        ]
        secondary_docs = [
            SummaryRecallDocument(page_content="s1", metadata={"doc_id": "d2"}),
            SummaryRecallDocument(page_content="s2", metadata={"doc_id": "d3"}),
        ]

        merged = merge_summary_recall_documents(
            settings=settings,
            primary_docs=primary_docs,
            secondary_docs=secondary_docs,
        )
        merged_ids = [doc.metadata["doc_id"] for doc in merged]

        self.assertEqual(merged_ids, ["d1", "d2", "d3"])

    def test_rrf_merge_beta_zero_prioritizes_lexical_only_docs(self):
        harness, *_ = self._build_harness()
        harness.config.rrf_k = 60
        harness.config.hybrid_beta = 0.0
        settings = harness.retrieval_settings_service.get_default()

        primary_docs = [
            SummaryRecallDocument(page_content="p1", metadata={"doc_id": "d1"}),
            SummaryRecallDocument(page_content="p2", metadata={"doc_id": "d2"}),
        ]
        secondary_docs = [
            SummaryRecallDocument(page_content="s1", metadata={"doc_id": "d2"}),
            SummaryRecallDocument(page_content="s2", metadata={"doc_id": "d3"}),
        ]

        merged = merge_summary_recall_documents(
            settings=settings,
            primary_docs=primary_docs,
            secondary_docs=secondary_docs,
        )
        merged_ids = [doc.metadata["doc_id"] for doc in merged]

        self.assertEqual(merged_ids, ["d2", "d3", "d1"])

    def test_build_rag_pipeline_returns_none_when_nothing_recalled(self):
        harness, *_ = self._build_harness()
        project = Project(user_id="u1", project_id="p1")

        with patch.object(
            harness.summary_recall_stage,
            "fuse_vector_and_lexical_recalls",
            return_value=VectorLexicalRecallBundle(
                vector_summary_docs=(),
                bm25_summary_docs=(),
                recalled_summary_docs=(),
            ),
        ):
            result = harness.use_cases.build_rag_pipeline.execute(project=project, question="q")

        self.assertIsNone(result)

    def test_build_rag_pipeline_success_builds_payload(self):
        harness, _, _evaluation_service, docstore_service, reranking_service = self._build_harness()
        project = Project(user_id="u1", project_id="p1")
        recalled_summary_docs = [
            SummaryRecallDocument(page_content="sum1", metadata={"doc_id": "d1"}),
            SummaryRecallDocument(page_content="sum2", metadata={"doc_id": "d2"}),
        ]
        raw_assets = [
            {"doc_id": "d1", "content_type": "text", "source_file": "f1", "raw_content": "raw", "metadata": {}}
        ]
        reranked_assets = [
            {
                "doc_id": "d1",
                "content_type": "text",
                "source_file": "f1",
                "raw_content": "raw",
                "metadata": {"rerank_score": 0.9},
                "summary": "summary",
            }
        ]
        prompt_sources_objs = [
            PromptSource(
                source_number=1,
                doc_id="d1",
                source_file="f1",
                content_type="text",
                page_label=None,
                locator_label=None,
                display_label="Source 1 — f1",
                prompt_label="[Source 1]",
                metadata={"rerank_score": 0.9},
            )
        ]

        with (
            patch.object(
                harness.summary_recall_stage.technical_ports.query_rewrite,
                "rewrite",
                return_value="rewritten",
            ),
            patch.object(
                harness.summary_recall_stage,
                "fuse_vector_and_lexical_recalls",
                return_value=VectorLexicalRecallBundle(
                    vector_summary_docs=tuple(recalled_summary_docs),
                    bm25_summary_docs=(),
                    recalled_summary_docs=tuple(recalled_summary_docs),
                ),
            ),
            patch.object(
                harness.post_recall_stage_services.prompt_source_service,
                "build_prompt_sources",
                return_value=prompt_sources_objs,
            ),
            patch.object(
                harness.post_recall_stage_services.prompt_builder_service,
                "build_raw_context",
                return_value="ctx",
            ),
            patch.object(
                harness.post_recall_stage_services.prompt_builder_service,
                "build_prompt",
                return_value="prompt",
            ),
        ):
            docstore_service.get_assets_by_doc_ids.return_value = raw_assets
            docstore_service.list_assets_for_source_file.return_value = raw_assets
            reranking_service.rerank.return_value = reranked_assets

            payload = harness.use_cases.build_rag_pipeline.execute(
                project=project, question="question", chat_history=["h1"]
            )

        self.assertIsNotNone(payload)
        self.assertEqual(payload.rewritten_question, "rewritten")
        self.assertEqual(payload.selected_doc_ids, ["d1"])
        self.assertEqual(payload.prompt_sources[0]["doc_id"], "d1")
        expected_confidence = ConfidenceService().compute_confidence(
            reranked_raw_assets=reranked_assets,
        )
        self.assertEqual(payload.confidence, expected_confidence)
        self.assertIsInstance(payload.latency, dict)
        self.assertGreaterEqual(payload.latency_ms, 0.0)
        lat = payload.latency
        for key in (
            "query_rewrite_ms",
            "retrieval_ms",
            "reranking_ms",
            "prompt_build_ms",
            "answer_generation_ms",
            "total_ms",
        ):
            self.assertIn(key, lat)
            self.assertGreaterEqual(lat[key], 0.0)
        self.assertEqual(lat["answer_generation_ms"], 0.0)
        self.assertEqual(payload.latency_ms, lat["total_ms"])
        self.assertEqual(payload.query_intent, QueryIntent.FACTUAL)
        self.assertEqual(len(payload.prompt_context_assets), 1)
        self.assertEqual(payload.section_expansion.recall_pool_size, 1)
        self.assertFalse(payload.image_context_enriched)
        self.assertEqual(
            payload.multimodal_analysis,
            {
                "has_text": True,
                "has_table": False,
                "has_image": False,
                "modality_count": 1,
            },
        )
        self.assertEqual(payload.multimodal_orchestration_hint, "")
        self.assertIsInstance(payload.context_compression, ContextCompressionStats)
        self.assertGreaterEqual(len(payload.pre_rerank_raw_assets), 1)

    @patch("src.infrastructure.adapters.rag.answer_generation_service.LLM")
    def test_ask_question_returns_rag_response(self, mock_llm):
        harness, *_ = self._build_harness()
        project = Project(user_id="u1", project_id="p1")
        pipeline = PipelineBuildResult(
            prompt="prompt text",
            selected_summary_docs=[SummaryRecallDocument(page_content="sum", metadata={"doc_id": "d1"})],
            reranked_raw_assets=[{"doc_id": "d1"}],
            prompt_sources=[{"doc_id": "d1"}],
            confidence=0.8,
            context_compression=ContextCompressionStats(
                enabled=True,
                applied=True,
                chars_before=100,
                chars_after=50,
                ratio=0.5,
            ),
            latency={
                "query_rewrite_ms": 0.1,
                "retrieval_ms": 0.2,
                "reranking_ms": 0.3,
                "prompt_build_ms": 0.4,
                "answer_generation_ms": 0.0,
                "total_ms": 1.0,
            },
        )
        mock_llm.invoke.return_value = SimpleNamespace(content=" final answer ")

        with patch.object(harness.use_cases.ask_question, "_retrieval") as mock_retrieval:
            mock_retrieval.execute.return_value = pipeline
            response = harness.use_cases.ask_question.execute(project=project, question="Q", chat_history=[])

        self.assertEqual(response.answer, "final answer")
        self.assertEqual(response.confidence, 0.8)
        self.assertIsNotNone(response.latency)
        self.assertGreaterEqual(response.latency["answer_generation_ms"], 0.0)
        self.assertGreater(response.latency["total_ms"], 0.0)

    @patch("src.infrastructure.adapters.rag.answer_generation_service.LLM")
    def test_ask_question_wraps_llm_errors(self, mock_llm):
        harness, *_ = self._build_harness()
        project = Project(user_id="u1", project_id="p1")
        mock_llm.invoke.side_effect = RuntimeError("timeout")
        pipeline = PipelineBuildResult(
            prompt="prompt text",
            selected_summary_docs=[],
            reranked_raw_assets=[],
            prompt_sources=[],
            confidence=0.0,
        )

        with patch.object(harness.use_cases.ask_question, "_retrieval") as mock_retrieval:
            mock_retrieval.execute.return_value = pipeline
            with self.assertRaises(LLMServiceError):
                harness.use_cases.ask_question.execute(project=project, question="Q", chat_history=[])

    @patch("src.infrastructure.adapters.rag.answer_generation_service.LLM")
    def test_ask_question_emits_query_log_when_configured(self, mock_llm):
        log_service = MagicMock()
        harness, *_ = self._build_harness(query_log_service=log_service)
        project = Project(user_id="u1", project_id="p1")
        pipeline = PipelineBuildResult(
            prompt="prompt text",
            rewritten_question="rw",
            selected_summary_docs=[],
            reranked_raw_assets=[],
            prompt_sources=[],
            confidence=0.7,
            selected_doc_ids=["d1"],
            recalled_doc_ids=["d1", "d2"],
            hybrid_retrieval_enabled=False,
            retrieval_mode="faiss",
            query_intent=QueryIntent.TABLE,
        )
        mock_llm.invoke.return_value = SimpleNamespace(content="ans")

        with patch.object(harness.use_cases.ask_question, "_retrieval") as retrieval_mock:
            retrieval_mock.execute.return_value = pipeline
            harness.use_cases.ask_question.execute(project=project, question="Q", chat_history=[])

        retrieval_mock.execute.assert_called_once()
        _, kwargs = retrieval_mock.execute.call_args
        self.assertFalse(kwargs.get("emit_query_log"))
        log_service.log_query.assert_called_once()
        payload = log_service.log_query.call_args.kwargs["payload"]
        self.assertEqual(payload["question"], "Q")
        self.assertEqual(payload["rewritten_query"], "rw")
        self.assertEqual(payload["project_id"], "p1")
        self.assertEqual(payload["user_id"], "u1")
        self.assertEqual(payload["selected_doc_ids"], ["d1"])
        self.assertEqual(payload["retrieved_doc_ids"], ["d1", "d2"])
        self.assertEqual(payload["answer"], "ans")
        self.assertEqual(payload["confidence"], 0.7)
        self.assertIsInstance(payload["latency_ms"], float)
        self.assertIn("query_rewrite_ms", payload)
        self.assertIn("total_latency_ms", payload)
        self.assertFalse(payload["hybrid_retrieval_enabled"])
        self.assertEqual(payload["retrieval_mode"], "faiss")
        self.assertEqual(payload["query_intent"], "table")


if __name__ == "__main__":
    unittest.main()
