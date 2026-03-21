from __future__ import annotations

from src.core.config import LLM
from src.core.exceptions import LLMServiceError
from src.domain.pipeline_payloads import PipelineBuildResult
from src.domain.project import Project


class AnswerGenerationService:
    """Invokes the configured LLM on a prepared RAG prompt."""

    def generate_answer(self, *, project: Project, pipeline: PipelineBuildResult) -> str:
        try:
            response = LLM.invoke(pipeline.prompt)
        except Exception as exc:
            raise LLMServiceError(
                f"Failed to generate answer for project '{project.project_id}': {exc}",
                user_message="The language model failed while generating the answer.",
            ) from exc

        return getattr(response, "content", str(response)).strip()
