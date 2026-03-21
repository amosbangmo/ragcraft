import unittest
from dataclasses import dataclass

from src.ui.evaluation_reports_tab import _is_benchmark_export_artifact


@dataclass(frozen=True)
class _FakeMeta:
    project_id: str = "p"


@dataclass(frozen=True)
class _FakeExport:
    metadata: _FakeMeta
    json_bytes: bytes = b"{}"
    csv_bytes: bytes = b""
    markdown_bytes: bytes = b"#"
    json_filename: str = "a.json"
    csv_filename: str = "a.csv"
    markdown_filename: str = "a.md"


class TestBenchmarkExportArtifactCheck(unittest.TestCase):
    def test_accepts_minimal_export_like_object(self) -> None:
        self.assertTrue(_is_benchmark_export_artifact(_FakeExport(metadata=_FakeMeta())))

    def test_rejects_none_and_partial(self) -> None:
        self.assertFalse(_is_benchmark_export_artifact(None))

        class Partial:
            json_bytes = b""

        self.assertFalse(_is_benchmark_export_artifact(Partial()))


if __name__ == "__main__":
    unittest.main()
