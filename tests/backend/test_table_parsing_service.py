import unittest

from src.infrastructure.services.table_parsing_service import TableParsingService


class TestTableParsingService(unittest.TestCase):
    def setUp(self) -> None:
        self.svc = TableParsingService()

    def test_simple_th_td_table(self) -> None:
        html = """
        <table>
          <tr><th>Name</th><th>Score</th></tr>
          <tr><td>Ann</td><td>10</td></tr>
          <tr><td>Bob</td><td>22</td></tr>
        </table>
        """
        out = self.svc.parse(html)
        self.assertEqual(out["headers"], ["Name", "Score"])
        self.assertEqual(out["rows"], [["Ann", "10"], ["Bob", "22"]])

    def test_thead_tbody(self) -> None:
        html = """
        <table>
          <thead><tr><th>A</th><th>B</th></tr></thead>
          <tbody><tr><td>1</td><td>2</td></tr></tbody>
        </table>
        """
        out = self.svc.parse(html)
        self.assertEqual(out["headers"], ["A", "B"])
        self.assertEqual(out["rows"], [["1", "2"]])

    def test_empty_and_non_table_returns_empty(self) -> None:
        self.assertEqual(self.svc.parse(""), {"headers": [], "rows": []})
        self.assertEqual(self.svc.parse("<p>no table</p>"), {"headers": [], "rows": []})

    def test_single_data_row_without_header_cells(self) -> None:
        html = "<table><tr><td>x</td><td>y</td></tr></table>"
        out = self.svc.parse(html)
        self.assertEqual(out["headers"], [])
        self.assertEqual(out["rows"], [["x", "y"]])


if __name__ == "__main__":
    unittest.main()
