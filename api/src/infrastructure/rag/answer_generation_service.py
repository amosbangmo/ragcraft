from __future__ import annotations

from domain.projects.project import Project
from domain.rag.pipeline_payloads import PipelineBuildResult
from infrastructure.config.config import LLM
from infrastructure.config.exceptions import LLMServiceError
from infrastructure.rag.llm.answer_generator import LLMAnswerGenerator


class AnswerGenerationService:
    """Invokes the configured LLM on a prepared RAG prompt."""

    def __init__(self, llm_answer_generator: LLMAnswerGenerator | None = None) -> None:
        self._llm = llm_answer_generator or LLMAnswerGenerator(LLM)

    def generate_answer(self, *, project: Project, pipeline: PipelineBuildResult) -> str:
        try:
            return self._llm.generate_answer_text(pipeline.prompt)
        except Exception as exc:
            raise LLMServiceError(
                f"Failed to generate answer for project '{project.project_id}': {exc}",
                user_message="The language model failed while generating the answer.",
            ) from exc
