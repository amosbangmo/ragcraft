import unittest

from langchain_core.documents import Document

from src.domain.retrieval_filters import (
    RetrievalFilters,
    filter_raw_assets_by_filters,
    filter_summary_documents_by_filters,
    raw_asset_matches_filters,
    summary_document_matches_filters,
    vector_search_fetch_k,
)


class TestRetrievalFilters(unittest.TestCase):
    def test_is_empty(self):
        self.assertTrue(RetrievalFilters().is_empty())
        self.assertFalse(RetrievalFilters(source_files=["a.pdf"]).is_empty())

    def test_to_dict_roundtrip_shape(self):
        f = RetrievalFilters(
            source_files=["x.pdf"],
            content_types=["text"],
            page_numbers=[1, 2],
            page_start=1,
            page_end=3,
        )
        d = f.to_dict()
        self.assertEqual(d["source_files"], ["x.pdf"])
        self.assertEqual(d["content_types"], ["text"])
        self.assertEqual(d["page_numbers"], [1, 2])
        self.assertEqual(d["page_start"], 1)
        self.assertEqual(d["page_end"], 3)

    def test_raw_asset_source_and_content_type(self):
        f = RetrievalFilters(source_files=["a.pdf"], content_types=["table"])
        asset_ok = {
            "source_file": "a.pdf",
            "content_type": "table",
            "metadata": {},
        }
        asset_wrong_file = {
            "source_file": "b.pdf",
            "content_type": "table",
            "metadata": {},
        }
        asset_wrong_type = {
            "source_file": "a.pdf",
            "content_type": "text",
            "metadata": {},
        }
        self.assertTrue(raw_asset_matches_filters(asset_ok, f))
        self.assertFalse(raw_asset_matches_filters(asset_wrong_file, f))
        self.assertFalse(raw_asset_matches_filters(asset_wrong_type, f))

    def test_content_type_case_insensitive(self):
        f = RetrievalFilters(content_types=["TEXT"])
        asset = {"source_file": "a.pdf", "content_type": "text", "metadata": {}}
        self.assertTrue(raw_asset_matches_filters(asset, f))

    def test_page_number_on_asset(self):
        f = RetrievalFilters(page_numbers=[2])
        self.assertTrue(
            raw_asset_matches_filters(
                {"source_file": "a.pdf", "content_type": "text", "metadata": {"page_number": 2}},
                f,
            )
        )
        self.assertFalse(
            raw_asset_matches_filters(
                {"source_file": "a.pdf", "content_type": "text", "metadata": {"page_number": 5}},
                f,
            )
        )

    def test_page_span_overlap(self):
        f = RetrievalFilters(page_numbers=[3])
        self.assertTrue(
            raw_asset_matches_filters(
                {
                    "source_file": "a.pdf",
                    "content_type": "text",
                    "metadata": {"page_start": 1, "page_end": 4},
                },
                f,
            )
        )
        self.assertFalse(
            raw_asset_matches_filters(
                {
                    "source_file": "a.pdf",
                    "content_type": "text",
                    "metadata": {"page_start": 10, "page_end": 12},
                },
                f,
            )
        )

    def test_page_range_filter_on_asset(self):
        f = RetrievalFilters(page_start=2, page_end=5)
        self.assertTrue(
            raw_asset_matches_filters(
                {
                    "source_file": "a.pdf",
                    "content_type": "text",
                    "metadata": {"page_number": 3},
                },
                f,
            )
        )
        self.assertFalse(
            raw_asset_matches_filters(
                {
                    "source_file": "a.pdf",
                    "content_type": "text",
                    "metadata": {"page_number": 9},
                },
                f,
            )
        )

    def test_page_filter_excludes_missing_metadata(self):
        f = RetrievalFilters(page_numbers=[1])
        self.assertFalse(
            raw_asset_matches_filters(
                {"source_file": "a.pdf", "content_type": "text", "metadata": {}},
                f,
            )
        )

    def test_reversed_page_span_in_metadata_normalized(self):
        f = RetrievalFilters(page_numbers=[2])
        self.assertTrue(
            raw_asset_matches_filters(
                {
                    "source_file": "a.pdf",
                    "content_type": "text",
                    "metadata": {"page_start": 5, "page_end": 1},
                },
                f,
            )
        )

    def test_summary_document_uses_file_name(self):
        f = RetrievalFilters(source_files=["doc.pdf"])
        doc = Document(page_content="x", metadata={"file_name": "doc.pdf", "content_type": "text"})
        self.assertTrue(summary_document_matches_filters(doc, f))

    def test_filter_raw_assets_preserves_order(self):
        assets = [
            {"doc_id": "1", "source_file": "a.pdf", "content_type": "text", "metadata": {}},
            {"doc_id": "2", "source_file": "b.pdf", "content_type": "text", "metadata": {}},
        ]
        f = RetrievalFilters(source_files=["b.pdf"])
        out = filter_raw_assets_by_filters(assets, f)
        self.assertEqual([a["doc_id"] for a in out], ["2"])

    def test_filter_summary_documents(self):
        docs = [
            Document(page_content="a", metadata={"doc_id": "1", "source_file": "x.pdf"}),
            Document(page_content="b", metadata={"doc_id": "2", "source_file": "y.pdf"}),
        ]
        f = RetrievalFilters(source_files=["y.pdf"])
        out = filter_summary_documents_by_filters(docs, f)
        self.assertEqual(len(out), 1)
        self.assertEqual(out[0].metadata["doc_id"], "2")

    def test_vector_search_fetch_k_unchanged_without_filters(self):
        self.assertEqual(vector_search_fetch_k(base_k=25, filters=None), 25)
        self.assertEqual(vector_search_fetch_k(base_k=25, filters=RetrievalFilters()), 25)

    def test_vector_search_fetch_k_overfetch_with_filters(self):
        f = RetrievalFilters(source_files=["a.pdf"])
        self.assertEqual(vector_search_fetch_k(base_k=25, filters=f), 100)
