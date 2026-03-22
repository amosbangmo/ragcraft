import unittest

from src.domain.retrieval_filters import RetrievalFilters
from src.backend.hybrid_retrieval_service import HybridRetrievalService


class TestHybridRetrievalMetadataFilters(unittest.TestCase):
    def test_lexical_search_restricts_bm25_corpus(self):
        svc = HybridRetrievalService()
        assets = [
            {
                "doc_id": "a1",
                "source_file": "f1.pdf",
                "content_type": "text",
                "raw_content": "uniquekeyword alpha",
                "summary": "s1",
                "metadata": {},
            },
            {
                "doc_id": "a2",
                "source_file": "f2.pdf",
                "content_type": "text",
                "raw_content": "uniquekeyword beta",
                "summary": "s2",
                "metadata": {},
            },
        ]
        f = RetrievalFilters(source_files=["f2.pdf"])
        docs = svc.lexical_search(query="uniquekeyword", assets=assets, k=10, filters=f)
        self.assertEqual(len(docs), 1)
        self.assertEqual(docs[0].metadata.get("doc_id"), "a2")
