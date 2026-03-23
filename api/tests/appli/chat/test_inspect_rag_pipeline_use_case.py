from __future__ import annotations

from unittest.mock import MagicMock

from application.use_cases.chat.inspect_rag_pipeline import InspectRagPipelineUseCase
from domain.projects.project import Project


def test_inspect_delegates_to_retrieval_port_with_query_log_disabled() -> None:
    retrieval = MagicMock(return_value=None)
    inspect = InspectRagPipelineUseCase(retrieval=retrieval)
    project = Project(user_id="u", project_id="p")

    inspect.execute(project, "question", ["h"])

    retrieval.execute.assert_called_once()
    ca = retrieval.execute.call_args
    assert ca.args == (project, "question", ["h"])
    assert ca.kwargs.get("emit_query_log") is False
