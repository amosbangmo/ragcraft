from __future__ import annotations

from unittest.mock import MagicMock

from src.application.use_cases.chat.inspect_rag_pipeline import InspectRagPipelineUseCase
from src.domain.project import Project


def test_inspect_delegates_with_emit_query_log_false() -> None:
    build = MagicMock()
    build.execute.return_value = None
    inspect = InspectRagPipelineUseCase(build_rag_pipeline=build)
    project = Project(user_id="u", project_id="p")

    inspect.execute(project, "question", ["h"])

    build.execute.assert_called_once()
    assert build.execute.call_args.kwargs["emit_query_log"] is False
