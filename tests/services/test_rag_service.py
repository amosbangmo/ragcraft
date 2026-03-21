import os
import sys
import types
import unittest
from dataclasses import asdict, is_dataclass
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

os.environ.setdefault("OPENAI_API_KEY", "test-key")

if "langchain_core.documents" not in sys.modules:
    # Lightweight substitute for LangChain's Document in test environment.
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
# Fill only the config attributes this service needs at import/runtime.
if not hasattr(config_module, "LLM"):
    config_module.LLM = SimpleNamespace(invoke=lambda prompt: SimpleNamespace(content="ok"))
if not hasattr(config_module, "RETRIEVAL_CONFIG"):
    config_module.RETRIEVAL_CONFIG = SimpleNamespace(
        query_rewrite_max_history_messages=6,
        max_text_chars_per_asset=4000,
        max_table_chars_per_asset=4000,
        enable_query_rewrite=True,
        enable_hybrid_retrieval=True,
        similarity_search_k=15,
        bm25_search_k=10,
        bm25_k1=1.5,
        bm25_b=0.75,
        bm25_epsilon=0.25,
        rrf_k=60,
        hybrid_beta=0.5,
        max_prompt_assets=5,
    )

if "src.services.hybrid_retrieval_service" not in sys.modules:
    # Avoid BM25 dependency for unit tests focused on RAG orchestration.
    hybrid_module = types.ModuleType("src.services.hybrid_retrieval_service")

    class HybridRetrievalService:
        def __init__(self, *, k1=1.5, b=0.75, epsilon=0.25):
            pass

        def lexical_search(self, *, query: str, assets: list[dict], k: int):
            return []

    hybrid_module.HybridRetrievalService = HybridRetrievalService
    sys.modules["src.services.hybrid_retrieval_service"] = hybrid_module

if "src.infrastructure.vectorstore.faiss_store" not in sys.modules:
    # Prevent FAISS import requirements when loading related services.
    faiss_store_module = types.ModuleType("src.infrastructure.vectorstore.faiss_store")

    def _noop(*args, **kwargs):
        return None

    faiss_store_module.load_vector_store = _noop
    faiss_store_module.save_vector_store = _noop
    faiss_store_module.create_or_update_vector_store = _noop
    faiss_store_module.delete_documents_from_vector_store = _noop
    sys.modules["src.infrastructure.vectorstore.faiss_store"] = faiss_store_module

from langchain_core.documents import Document
from src.core.exceptions import LLMServiceError
from src.domain.project import Project
from src.domain.source_citation import SourceCitation
from src.services.confidence_service import ConfidenceService
from src.services.rag_service import RAGService


def _mutable_retrieval_config_view(cfg):
    """RAGService tests mutate ``service.config``; real ``RetrievalConfig`` is frozen."""
    if is_dataclass(cfg) and cfg.__dataclass_params__.frozen:
        return SimpleNamespace(**asdict(cfg))
    return cfg


class TestRAGService(unittest.TestCase):
    def _build_service(self, query_log_service=None):
        vectorstore_service = MagicMock()
        evaluation_service = MagicMock()
        docstore_service = MagicMock()
        reranking_service = MagicMock()
        service = RAGService(
            vectorstore_service=vectorstore_service,
            evaluation_service=evaluation_service,
            docstore_service=docstore_service,
            reranking_service=reranking_service,
            query_log_service=query_log_service,
        )
        service.config = _mutable_retrieval_config_view(service.config)
        # Match stable RRF expectations; real ``RetrievalConfig`` may come from env.
        service.config.hybrid_beta = 0.5
        service.config.rrf_k = 60
        return (
            service,
            vectorstore_service,
            evaluation_service,
            docstore_service,
            reranking_service,
        )

    def test_deduplicate_doc_ids_preserves_order(self):
        service, *_ = self._build_service()
        docs = [
            Document(page_content="a", metadata={"doc_id": "d1"}),
            Document(page_content="b", metadata={"doc_id": "d2"}),
            Document(page_content="c", metadata={"doc_id": "d1"}),
            Document(page_content="d", metadata={}),
        ]

        result = service._deduplicate_doc_ids(docs)

        self.assertEqual(result, ["d1", "d2"])

    def test_rrf_merge_prioritizes_common_docs(self):
        service, *_ = self._build_service()
        service.config.rrf_k = 60

        # ranks: d1(1), d2(2) in primary; d2(1), d3(2) in secondary
        primary_docs = [
            Document(page_content="p1", metadata={"doc_id": "d1"}),
            Document(page_content="p2", metadata={"doc_id": "d2"}),
        ]
        secondary_docs = [
            Document(page_content="s1", metadata={"doc_id": "d2"}),
            Document(page_content="s2", metadata={"doc_id": "d3"}),
        ]

        merged = service._merge_summary_docs(primary_docs=primary_docs, secondary_docs=secondary_docs)
        merged_ids = [doc.metadata["doc_id"] for doc in merged]

        # d2 appears in both lists at rank 1 in secondary and rank 2 in primary, so it should win.
        self.assertEqual(merged_ids[:2], ["d2", "d1"])

    def test_rrf_merge_respects_max_docs(self):
        service, *_ = self._build_service()
        service.config.rrf_k = 60

        primary_docs = [
            Document(page_content="p1", metadata={"doc_id": "d1"}),
            Document(page_content="p2", metadata={"doc_id": "d2"}),
        ]
        secondary_docs = [
            Document(page_content="s1", metadata={"doc_id": "d2"}),
            Document(page_content="s2", metadata={"doc_id": "d3"}),
        ]

        merged = service._merge_summary_docs(
            primary_docs=primary_docs,
            secondary_docs=secondary_docs,
            max_docs=2,
        )
        merged_ids = [doc.metadata["doc_id"] for doc in merged]
        self.assertEqual(merged_ids, ["d2", "d1"])

    def test_rrf_merge_beta_one_prioritizes_semantic_only_docs(self):
        service, *_ = self._build_service()
        service.config.rrf_k = 60
        service.config.hybrid_beta = 1.0

        primary_docs = [
            Document(page_content="p1", metadata={"doc_id": "d1"}),
            Document(page_content="p2", metadata={"doc_id": "d2"}),
        ]
        secondary_docs = [
            Document(page_content="s1", metadata={"doc_id": "d2"}),
            Document(page_content="s2", metadata={"doc_id": "d3"}),
        ]

        merged = service._merge_summary_docs(primary_docs=primary_docs, secondary_docs=secondary_docs)
        merged_ids = [doc.metadata["doc_id"] for doc in merged]

        self.assertEqual(merged_ids, ["d1", "d2", "d3"])

    def test_rrf_merge_beta_zero_prioritizes_lexical_only_docs(self):
        service, *_ = self._build_service()
        service.config.rrf_k = 60
        service.config.hybrid_beta = 0.0

        primary_docs = [
            Document(page_content="p1", metadata={"doc_id": "d1"}),
            Document(page_content="p2", metadata={"doc_id": "d2"}),
        ]
        secondary_docs = [
            Document(page_content="s1", metadata={"doc_id": "d2"}),
            Document(page_content="s2", metadata={"doc_id": "d3"}),
        ]

        merged = service._merge_summary_docs(primary_docs=primary_docs, secondary_docs=secondary_docs)
        merged_ids = [doc.metadata["doc_id"] for doc in merged]

        self.assertEqual(merged_ids, ["d2", "d3", "d1"])

    def test_run_pipeline_returns_none_when_nothing_recalled(self):
        service, *_ = self._build_service()
        project = Project(user_id="u1", project_id="p1")

        with patch.object(
            service,
            "_retrieve_summary_docs",
            return_value={"vector_summary_docs": [], "bm25_summary_docs": [], "recalled_summary_docs": []},
        ):
            result = service._run_pipeline(project=project, question="q")

        self.assertIsNone(result)

    def test_run_pipeline_success_builds_payload(self):
        # Validate the orchestration path from retrieval to prompt payload fields.
        service, _, _evaluation_service, docstore_service, reranking_service = self._build_service()
        project = Project(user_id="u1", project_id="p1")
        recalled_summary_docs = [
            Document(page_content="sum1", metadata={"doc_id": "d1"}),
            Document(page_content="sum2", metadata={"doc_id": "d2"}),
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
        citations = [
            SourceCitation(
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
            patch.object(service, "_rewrite_question", return_value="rewritten"),
            patch.object(
                service,
                "_retrieve_summary_docs",
                return_value={
                    "vector_summary_docs": recalled_summary_docs,
                    "bm25_summary_docs": [],
                    "recalled_summary_docs": recalled_summary_docs,
                },
            ),
            patch.object(service.source_citation_service, "build_citations", return_value=citations),
            patch.object(service.prompt_builder_service, "build_raw_context", return_value="ctx"),
            patch.object(service.prompt_builder_service, "build_prompt", return_value="prompt"),
        ):
            docstore_service.get_assets_by_doc_ids.return_value = raw_assets
            reranking_service.rerank.return_value = reranked_assets

            payload = service._run_pipeline(project=project, question="question", chat_history=["h1"])

        self.assertIsNotNone(payload)
        self.assertEqual(payload["rewritten_question"], "rewritten")
        self.assertEqual(payload["selected_doc_ids"], ["d1"])
        self.assertEqual(payload["source_references"][0]["doc_id"], "d1")
        expected_confidence = ConfidenceService().compute_confidence(
            reranked_raw_assets=reranked_assets,
        )
        self.assertEqual(payload["confidence"], expected_confidence)
        self.assertIn("latency", payload)
        self.assertIn("latency_ms", payload)
        lat = payload["latency"]
        self.assertIsInstance(lat, dict)
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
        self.assertEqual(payload["latency_ms"], lat["total_ms"])

    @patch("src.services.rag_service.LLM")
    def test_ask_returns_rag_response(self, mock_llm):
        service, *_ = self._build_service()
        project = Project(user_id="u1", project_id="p1")
        pipeline = {
            "prompt": "prompt text",
            "selected_summary_docs": [Document(page_content="sum", metadata={"doc_id": "d1"})],
            "reranked_raw_assets": [{"doc_id": "d1"}],
            "source_references": [{"doc_id": "d1"}],
            "confidence": 0.8,
            "latency": {
                "query_rewrite_ms": 0.1,
                "retrieval_ms": 0.2,
                "reranking_ms": 0.3,
                "prompt_build_ms": 0.4,
                "answer_generation_ms": 0.0,
                "total_ms": 1.0,
            },
        }
        mock_llm.invoke.return_value = SimpleNamespace(content=" final answer ")

        with patch.object(service, "_run_pipeline", return_value=pipeline):
            response = service.ask(project=project, question="Q", chat_history=[])

        self.assertEqual(response.answer, "final answer")
        self.assertEqual(response.confidence, 0.8)
        self.assertIsNotNone(response.latency)
        self.assertGreaterEqual(response.latency["answer_generation_ms"], 0.0)
        self.assertGreater(response.latency["total_ms"], 0.0)

    @patch("src.services.rag_service.LLM")
    def test_ask_wraps_llm_errors(self, mock_llm):
        service, *_ = self._build_service()
        project = Project(user_id="u1", project_id="p1")
        mock_llm.invoke.side_effect = RuntimeError("timeout")
        pipeline = {
            "prompt": "prompt text",
            "selected_summary_docs": [],
            "reranked_raw_assets": [],
            "source_references": [],
            "confidence": 0.0,
        }

        with patch.object(service, "_run_pipeline", return_value=pipeline):
            with self.assertRaises(LLMServiceError):
                service.ask(project=project, question="Q", chat_history=[])

    @patch("src.services.rag_service.LLM")
    def test_ask_emits_query_log_when_configured(self, mock_llm):
        log_service = MagicMock()
        service, *_ = self._build_service(query_log_service=log_service)
        project = Project(user_id="u1", project_id="p1")
        pipeline = {
            "prompt": "prompt text",
            "rewritten_question": "rw",
            "selected_summary_docs": [],
            "reranked_raw_assets": [],
            "source_references": [],
            "confidence": 0.7,
            "selected_doc_ids": ["d1"],
            "recalled_doc_ids": ["d1", "d2"],
            "hybrid_retrieval_enabled": False,
            "retrieval_mode": "faiss",
        }
        mock_llm.invoke.return_value = SimpleNamespace(content="ans")

        with patch.object(service, "_run_pipeline", return_value=pipeline) as run_pipeline:
            service.ask(project=project, question="Q", chat_history=[])

        run_pipeline.assert_called_once()
        _, kwargs = run_pipeline.call_args
        self.assertTrue(kwargs.get("defer_query_log"))
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


if __name__ == "__main__":
    unittest.main()
