import unittest

from src.infrastructure.services.answer_citation_metrics_service import (
    answer_cited_doc_ids,
    extract_cited_source_numbers,
)


class TestAnswerCitationMetricsService(unittest.TestCase):
    def test_extract_single_source(self) -> None:
        self.assertEqual(extract_cited_source_numbers("See [Source 1] for details."), {1})

    def test_extract_case_insensitive(self) -> None:
        self.assertEqual(extract_cited_source_numbers("Ref [source 2] and [SOURCE 3]."), {2, 3})

    def test_extract_table_suffix_same_bracket_group_not_double_counted(self) -> None:
        s = "Data [Source 1][Table: Sales] and [Source 2]."
        self.assertEqual(extract_cited_source_numbers(s), {1, 2})

    def test_unknown_source_number_ignored_for_doc_ids(self) -> None:
        refs = [
            {"source_number": 1, "doc_id": "d-a"},
            {"source_number": 2, "doc_id": "d-b"},
        ]
        ans = "Citing [Source 99] only."
        self.assertEqual(answer_cited_doc_ids(answer=ans, prompt_sources=refs), set())

    def test_maps_without_source_number_uses_order(self) -> None:
        refs = [{"doc_id": "x"}, {"doc_id": "y"}]
        ans = "First [Source 1] second [Source 2]."
        self.assertEqual(answer_cited_doc_ids(answer=ans, prompt_sources=refs), {"x", "y"})

    def test_empty_answer(self) -> None:
        self.assertEqual(answer_cited_doc_ids(answer="", prompt_sources=[{"doc_id": "z"}]), set())


if __name__ == "__main__":
    unittest.main()
