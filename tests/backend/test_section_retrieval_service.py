import unittest
from dataclasses import replace

from src.core.config import RETRIEVAL_CONFIG
from src.backend.section_retrieval_service import SectionRetrievalService


def _cfg(**kwargs):
    return replace(RETRIEVAL_CONFIG, **kwargs)


class TestSectionRetrievalService(unittest.TestCase):
    def test_no_metadata_signals_no_expansion(self):
        svc = SectionRetrievalService()
        retrieved = [{"doc_id": "a", "source_file": "f.pdf", "metadata": {}}]
        corpus = retrieved + [{"doc_id": "b", "source_file": "f.pdf", "metadata": {}}]
        out = svc.expand(
            config=_cfg(enable_section_expansion=True),
            retrieved_assets=retrieved,
            all_assets=corpus,
        )
        self.assertFalse(out.applied)
        self.assertEqual(out.section_expansion_count, 0)
        self.assertEqual([a["doc_id"] for a in out.assets], ["a"])

    def test_same_chunk_title_brings_siblings(self):
        svc = SectionRetrievalService()
        m = {"chunk_title": "Intro", "section_id": "Intro"}
        retrieved = [{"doc_id": "a", "source_file": "f.pdf", "metadata": {**m}}]
        corpus = retrieved + [
            {"doc_id": "b", "source_file": "f.pdf", "metadata": {**m}},
            {"doc_id": "c", "source_file": "f.pdf", "metadata": {"chunk_title": "Other"}},
        ]
        out = svc.expand(
            config=_cfg(
                enable_section_expansion=True,
                section_expansion_max_per_section=10,
                section_expansion_global_max=20,
            ),
            retrieved_assets=retrieved,
            all_assets=corpus,
        )
        ids = {a["doc_id"] for a in out.assets}
        self.assertEqual(ids, {"a", "b"})

    def test_element_neighbor_window(self):
        svc = SectionRetrievalService()
        retrieved = [
            {
                "doc_id": "a",
                "source_file": "f.pdf",
                "metadata": {"start_element_index": 2, "end_element_index": 2},
            }
        ]
        corpus = retrieved + [
            {
                "doc_id": "b",
                "source_file": "f.pdf",
                "metadata": {"start_element_index": 4, "end_element_index": 4},
            },
            {
                "doc_id": "c",
                "source_file": "f.pdf",
                "metadata": {"start_element_index": 10, "end_element_index": 10},
            },
        ]
        out = svc.expand(
            config=_cfg(
                enable_section_expansion=True,
                section_expansion_neighbor_window=1,
                section_expansion_global_max=10,
                section_expansion_max_per_section=10,
            ),
            retrieved_assets=retrieved,
            all_assets=corpus,
        )
        ids = {a["doc_id"] for a in out.assets}
        self.assertEqual(ids, {"a", "b"})

    def test_no_duplicate_doc_ids_in_pool(self):
        svc = SectionRetrievalService()
        retrieved = [
            {
                "doc_id": "a",
                "source_file": "f.pdf",
                "metadata": {"start_element_index": 0, "end_element_index": 0},
            }
        ]
        b = {
            "doc_id": "b",
            "source_file": "f.pdf",
            "metadata": {"start_element_index": 1, "end_element_index": 1},
        }
        corpus = retrieved + [b, dict(b)]
        out = svc.expand(
            config=_cfg(enable_section_expansion=True, section_expansion_neighbor_window=2),
            retrieved_assets=retrieved,
            all_assets=corpus,
        )
        self.assertEqual(len(out.assets), 2)
        self.assertEqual(len({a["doc_id"] for a in out.assets}), 2)

    def test_respects_global_max(self):
        svc = SectionRetrievalService()
        retrieved = [
            {
                "doc_id": "s0",
                "source_file": "f.pdf",
                "metadata": {"start_element_index": 0, "end_element_index": 0},
            }
        ]
        extras = [
            {
                "doc_id": f"s{i}",
                "source_file": "f.pdf",
                "metadata": {"start_element_index": i, "end_element_index": i},
            }
            for i in range(1, 10)
        ]
        corpus = retrieved + extras
        out = svc.expand(
            config=_cfg(
                enable_section_expansion=True,
                section_expansion_neighbor_window=5,
                section_expansion_global_max=3,
                section_expansion_max_per_section=20,
            ),
            retrieved_assets=retrieved,
            all_assets=corpus,
        )
        self.assertLessEqual(len(out.assets), 3)

    def test_disabled_returns_retrieved_only(self):
        svc = SectionRetrievalService()
        m = {"chunk_title": "Same"}
        retrieved = [{"doc_id": "a", "source_file": "f.pdf", "metadata": {**m}}]
        corpus = retrieved + [{"doc_id": "b", "source_file": "f.pdf", "metadata": {**m}}]
        out = svc.expand(
            config=_cfg(enable_section_expansion=False),
            retrieved_assets=retrieved,
            all_assets=corpus,
        )
        self.assertFalse(out.applied)
        self.assertEqual(len(out.assets), 1)


if __name__ == "__main__":
    unittest.main()
