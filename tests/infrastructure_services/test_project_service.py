import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from src.infrastructure.adapters.workspace.project_service import ProjectService


class TestProjectService(unittest.TestCase):
    def test_list_projects_empty_user(self) -> None:
        svc = ProjectService(data_root=Path("/tmp/unused"))
        self.assertEqual(svc.list_projects(None), [])
        self.assertEqual(svc.list_projects(""), [])

    def test_create_list_documents_and_get_project(self) -> None:
        with TemporaryDirectory() as tmp:
            root = Path(tmp) / "data"
            svc = ProjectService(data_root=root)
            svc.create_project("user1", "proj-a")
            svc.create_project("user1", "proj-b")
            names = svc.list_projects("user1")
            self.assertEqual(names, ["proj-a", "proj-b"])

            doc_path = (
                root / "users" / "user1" / "projects" / "proj-a" / "readme.txt"
            )
            doc_path.parent.mkdir(parents=True, exist_ok=True)
            doc_path.write_text("hi", encoding="utf-8")

            docs = svc.list_project_documents("user1", "proj-a")
            self.assertEqual(docs, ["readme.txt"])

            missing_docs = svc.list_project_documents("user1", "no-such")
            self.assertEqual(missing_docs, [])


if __name__ == "__main__":
    unittest.main()
