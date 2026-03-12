from pathlib import Path
from src.domain.project import Project


class ProjectService:
    def __init__(self, data_root: str = "data"):
        self.data_root = Path(data_root)

    def get_project(self, user_id: str, project_id: str) -> Project:
        return Project(user_id=user_id, project_id=project_id, data_root=self.data_root)

    def create_project(self, user_id: str, project_id: str) -> Project:
        project = self.get_project(user_id, project_id)
        project.path.mkdir(parents=True, exist_ok=True)
        return project

    def list_projects(self, user_id: str) -> list[str]:
        user_path = self.data_root / f"user_{user_id}"
        user_path.mkdir(parents=True, exist_ok=True)
        return sorted([p.name for p in user_path.iterdir() if p.is_dir()])
