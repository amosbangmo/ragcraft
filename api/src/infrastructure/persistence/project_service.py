from pathlib import Path

from infrastructure.config.paths import get_data_root
from domain.projects.project import Project


class ProjectService:
    def __init__(self, data_root: str | Path | None = None):
        resolved_root = Path(data_root) if data_root is not None else get_data_root()
        self.data_root = resolved_root

    def get_project(self, user_id: str, project_id: str) -> Project:
        return Project(user_id=user_id, project_id=project_id, data_root=self.data_root)

    def create_project(self, user_id: str, project_id: str) -> Project:
        project = self.get_project(user_id, project_id)
        project.path.mkdir(parents=True, exist_ok=True)
        return project

    def list_projects(self, user_id: str | None) -> list[str]:
        if not user_id:
            return []

        user_projects_path = self.data_root / "users" / user_id / "projects"
        user_projects_path.mkdir(parents=True, exist_ok=True)
        return sorted([p.name for p in user_projects_path.iterdir() if p.is_dir()])

    def list_project_documents(self, user_id: str, project_id: str) -> list[str]:
        project = self.get_project(user_id, project_id)

        if not project.path.exists():
            return []

        ignored_names = {"faiss_index", "logs.json"}

        documents = [
            item.name
            for item in project.path.iterdir()
            if item.is_file() and item.name not in ignored_names
        ]

        return sorted(documents)
