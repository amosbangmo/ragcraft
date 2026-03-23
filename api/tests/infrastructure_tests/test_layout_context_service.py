import unittest

from infrastructure.rag.layout_context_service import (
    LayoutContextService,
    describe_layout_group,
)


class TestLayoutContextService(unittest.TestCase):
    def setUp(self) -> None:
        self.svc = LayoutContextService()

    def test_empty(self) -> None:
        self.assertEqual(self.svc.group_assets([]), [])

    def test_single_asset(self) -> None:
        a = {"doc_id": "1", "source_file": "f.pdf", "metadata": {"page_number": 1}}
        g = self.svc.group_assets([a])
        self.assertEqual(len(g), 1)
        self.assertIs(g[0][0], a)

    def test_validate_groups_identity_order(self) -> None:
        assets = [
            {"doc_id": "1", "metadata": {"page_number": 1}},
            {"doc_id": "2", "metadata": {"page_number": 1}},
        ]
        groups = self.svc.group_assets(assets)
        self.assertTrue(self.svc.validate_groups(assets, groups))

    def test_page_change_starts_new_group(self) -> None:
        a = {
            "source_file": "f.pdf",
            "content_type": "text",
            "metadata": {"page_number": 1, "chunk_title": "Intro", "start_element_index": 0, "end_element_index": 0},
        }
        b = {
            "source_file": "f.pdf",
            "content_type": "text",
            "metadata": {"page_number": 2, "chunk_title": "Intro", "start_element_index": 1, "end_element_index": 1},
        }
        groups = self.svc.group_assets([a, b])
        self.assertEqual(len(groups), 2)

    def test_large_element_gap_splits_same_page(self) -> None:
        a = {
            "source_file": "f.pdf",
            "content_type": "text",
            "metadata": {"page_number": 1, "chunk_title": "X", "start_element_index": 0, "end_element_index": 0},
        }
        b = {
            "source_file": "f.pdf",
            "content_type": "text",
            "metadata": {"page_number": 1, "chunk_title": "X", "start_element_index": 10, "end_element_index": 10},
        }
        groups = self.svc.group_assets([a, b])
        self.assertEqual(len(groups), 2)

    def test_describe_layout_group(self) -> None:
        g = [
            {
                "source_file": "r.pdf",
                "metadata": {"page_number": 3, "chunk_title": "Methods"},
            }
        ]
        title = describe_layout_group(g)
        self.assertIn("Page 3", title)
        self.assertIn("Methods", title)
        self.assertIn("r.pdf", title)


class TestLayoutFallback(unittest.TestCase):
    def test_validate_rejects_wrong_length(self) -> None:
        svc = LayoutContextService()
        assets = [{"doc_id": "1"}, {"doc_id": "2"}]
        self.assertFalse(svc.validate_groups(assets, [[assets[0]]]))


if __name__ == "__main__":
    unittest.main()
