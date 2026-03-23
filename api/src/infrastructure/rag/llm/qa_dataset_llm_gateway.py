"""
LLM-backed proposal generation for gold QA datasets: prompt construction, invocation, and JSON parsing.

Keeps provider-specific prompting out of application use cases.
"""

from __future__ import annotations

import json
import re

from infrastructure.config.config import LLM


class QADatasetLlmGateway:
    """Infrastructure gateway for QA dataset LLM calls."""

    def generate_qa_entry_dicts(
        self,
        *,
        project_id: str,
        num_questions: int,
        source_files: list[str],
        context: str,
    ) -> list[dict]:
        prompt = _build_generation_prompt(
            project_id=project_id,
            num_questions=num_questions,
            source_files=source_files,
            context=context,
        )
        response = LLM.invoke(prompt)
        content = getattr(response, "content", str(response)).strip()
        generated_entries = _parse_generated_entries(content)

        if not generated_entries:
            raise ValueError("The model did not return any valid QA entries.")

        return generated_entries[:num_questions]


def _build_generation_prompt(
    *,
    project_id: str,
    num_questions: int,
    source_files: list[str],
    context: str,
) -> str:
    source_file_list = ", ".join(source_files)

    return f"""
You are generating a gold QA dataset for a Retrieval-Augmented Generation project.

Project:
- project_id: {project_id}
- source_files: {source_file_list}

Goal:
Generate exactly {num_questions} realistic benchmark QA entries grounded ONLY in the provided document assets.

Requirements:
- Return valid JSON only.
- Return a JSON array.
- Each item must contain:
  - "question": string
  - "expected_answer": string
  - "expected_doc_ids": array of strings
  - "expected_sources": array of strings
- Each question must be answerable from the provided context.
- Keep expected_doc_ids focused: usually 1 to 3 ids max.
- expected_sources must contain the supporting source file names.
- Prefer factual, retrieval-friendly questions.
- Include a mix of:
  - direct factual questions
  - synthesis questions
  - table-oriented questions when tables are available
- Do not invent unsupported information.
- Do not include markdown fences.
- Do not include explanations before or after the JSON.

Document asset context:
{context}
"""


def _parse_generated_entries(raw_output: str) -> list[dict]:
    candidate_text = extract_json_array(raw_output)

    try:
        payload = json.loads(candidate_text)
    except json.JSONDecodeError as exc:
        raise ValueError(f"Unable to parse generated QA dataset JSON: {exc}") from exc

    if not isinstance(payload, list):
        raise ValueError("Generated QA dataset payload must be a JSON array.")

    normalized_entries: list[dict] = []

    for item in payload:
        if not isinstance(item, dict):
            continue

        question = (item.get("question") or "").strip()
        expected_answer = (item.get("expected_answer") or "").strip()

        expected_doc_ids = _normalize_string_list(item.get("expected_doc_ids"))
        expected_sources = _normalize_string_list(item.get("expected_sources"))

        if not question:
            continue

        normalized_entries.append(
            {
                "question": question,
                "expected_answer": expected_answer or None,
                "expected_doc_ids": expected_doc_ids,
                "expected_sources": expected_sources,
            }
        )

    return normalized_entries


def extract_json_array(raw_output: str) -> str:
    """Extract a JSON array substring from model output (strips common markdown fences)."""
    cleaned = raw_output.strip()

    if cleaned.startswith("```"):
        cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned)
        cleaned = re.sub(r"\s*```$", "", cleaned)

    start = cleaned.find("[")
    end = cleaned.rfind("]")

    if start == -1 or end == -1 or end < start:
        raise ValueError("The model response does not contain a JSON array.")

    return cleaned[start : end + 1]


def _normalize_string_list(values) -> list[str]:
    if not isinstance(values, list):
        return []

    normalized: list[str] = []
    seen: set[str] = set()

    for value in values:
        cleaned = str(value or "").strip()
        if not cleaned or cleaned in seen:
            continue
        seen.add(cleaned)
        normalized.append(cleaned)

    return normalized
