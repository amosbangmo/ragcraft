from dataclasses import dataclass, field
from pathlib import Path

from infrastructure.config.paths import get_data_root


@dataclass(frozen=True)
class Project:
    user_id: str
    project_id: str
    data_root: Path = field(default_factory=get_data_root)

    @property
    def user_path(self) -> Path:
        return self.data_root / "users" / self.user_id

    @property
    def projects_path(self) -> Path:
        return self.user_path / "projects"

    @property
    def path(self) -> Path:
        return self.projects_path / self.project_id

    @property
    def faiss_index_path(self) -> Path:
        return self.path / "faiss_index"
