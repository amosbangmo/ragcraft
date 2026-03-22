from __future__ import annotations

from src.core.config import LLM
from src.core.exceptions import LLMServiceError
from src.domain.pipeline_payloads import PipelineBuildResult
from src.domain.project import Project
from src.infrastructure.llm.answer_generator import LLMAnswerGenerator


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
