from __future__ import annotations

from unittest.mock import MagicMock

from src.application.use_cases.chat.inspect_rag_pipeline import InspectRagPipelineUseCase
from src.domain.project import Project


def test_inspect_delegates_to_injected_build_pipeline() -> None:
    build_pipeline = MagicMock(return_value=None)
    inspect = InspectRagPipelineUseCase(build_pipeline=build_pipeline)
    project = Project(user_id="u", project_id="p")

    inspect.execute(project, "question", ["h"])

    build_pipeline.assert_called_once()
    ca = build_pipeline.call_args
    assert ca.args == (project, "question", ["h"])
    assert "emit_query_log" not in ca.kwargs
