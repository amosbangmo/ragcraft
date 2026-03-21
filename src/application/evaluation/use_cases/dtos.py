from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class GenerateQaDatasetCommand:
    user_id: str
    project_id: str
    num_questions: int
    source_files: list[str] | None = None
    generation_mode: str = "append"
