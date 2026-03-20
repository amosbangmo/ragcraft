import json
import re

from src.core.config import LLM
from src.services.docstore_service import DocStoreService
from src.services.project_service import ProjectService


MAX_ASSETS_PER_GENERATION = 12
MAX_TEXT_CHARS_PER_ASSET = 1400
MAX_TABLE_CHARS_PER_ASSET = 1200
MAX_CONTEXT_CHARS = 18000


class QADatasetGenerationService:
    def __init__(
        self,
        *,
        docstore_service: DocStoreService,
        project_service: ProjectService,
    ):
        self.docstore_service = docstore_service
        self.project_service = project_service

    def generate_entries(
        self,
        *,
        user_id: str,
        project_id: str,
        num_questions: int,
        source_files: list[str] | None = None,
    ) -> list[dict]:
        normalized_num_questions = max(1, min(int(num_questions), 20))
        selected_source_files = self._resolve_source_files(
            user_id=user_id,
            project_id=project_id,
            source_files=source_files,
        )

        if not selected_source_files:
            raise ValueError("No project documents are available for QA generation.")

        raw_assets = self._collect_assets(
            user_id=user_id,
            project_id=project_id,
            source_files=selected_source_files,
        )

        if not raw_assets:
            raise ValueError("No indexed assets are available for the selected project documents.")

        context = self._build_generation_context(raw_assets)
        prompt = self._build_prompt(
            project_id=project_id,
            num_questions=normalized_num_questions,
            source_files=selected_source_files,
            context=context,
        )

        response = LLM.invoke(prompt)
        content = getattr(response, "content", str(response)).strip()

        generated_entries = self._parse_generated_entries(content)

        if not generated_entries:
            raise ValueError("The model did not return any valid QA entries.")

        return generated_entries[:normalized_num_questions]

    def _resolve_source_files(
        self,
        *,
        user_id: str,
        project_id: str,
        source_files: list[str] | None,
    ) -> list[str]:
        project_documents = self.project_service.list_project_documents(
            user_id=user_id,
            project_id=project_id,
        )

        if not project_documents:
            return []

        if not source_files:
            return project_documents

        normalized_selection = []
        available_set = set(project_documents)

        for name in source_files:
            cleaned = (name or "").strip()
            if cleaned and cleaned in available_set and cleaned not in normalized_selection:
                normalized_selection.append(cleaned)

        return normalized_selection

    def _collect_assets(
        self,
        *,
        user_id: str,
        project_id: str,
        source_files: list[str],
    ) -> list[dict]:
        assets: list[dict] = []

        for source_file in source_files:
            source_assets = self.docstore_service.list_assets_for_source_file(
                user_id=user_id,
                project_id=project_id,
                source_file=source_file,
            )
            assets.extend(source_assets)

        prioritized_assets = sorted(
            assets,
            key=self._asset_priority,
        )

        return prioritized_assets[:MAX_ASSETS_PER_GENERATION]

    def _asset_priority(self, asset: dict) -> tuple[int, str, str]:
        content_type = asset.get("content_type", "unknown")
        source_file = asset.get("source_file", "unknown")
        doc_id = asset.get("doc_id", "")

        if content_type == "text":
            rank = 0
        elif content_type == "table":
            rank = 1
        elif content_type == "image":
            rank = 2
        else:
            rank = 3

        return (rank, source_file, doc_id)

    def _build_generation_context(self, assets: list[dict]) -> str:
        blocks: list[str] = []
        current_total_chars = 0

        for asset in assets:
            block = self._format_asset_block(asset)

            if not block:
                continue

            projected = current_total_chars + len(block)
            if projected > MAX_CONTEXT_CHARS:
                break

            blocks.append(block)
            current_total_chars = projected

        if not blocks:
            raise ValueError("Unable to build a QA generation context from indexed assets.")

        return "\n\n".join(blocks)

    def _format_asset_block(self, asset: dict) -> str:
        content_type = asset.get("content_type", "unknown")
        source_file = asset.get("source_file", "unknown")
        doc_id = asset.get("doc_id", "?")
        metadata = asset.get("metadata", {}) or {}
        summary = (asset.get("summary", "") or "").strip()
        raw_content = (asset.get("raw_content", "") or "").strip()

        page_label = self._build_page_label(metadata)
        locator_parts = []

        if page_label:
            locator_parts.append(page_label)

        if content_type == "table" and metadata.get("table_title"):
            locator_parts.append(f"table={metadata.get('table_title')}")
        if content_type == "image" and metadata.get("image_title"):
            locator_parts.append(f"figure={metadata.get('image_title')}")
        if content_type == "text":
            start_idx = metadata.get("start_element_index")
            end_idx = metadata.get("end_element_index")
            if start_idx is not None and end_idx is not None:
                locator_parts.append(f"elements={start_idx}-{end_idx}")

        locator_text = " | ".join(locator_parts) if locator_parts else "no-locator"

        if content_type == "text":
            raw_preview = raw_content[:MAX_TEXT_CHARS_PER_ASSET]
        elif content_type == "table":
            table_text = (metadata.get("table_text") or raw_content)[:MAX_TABLE_CHARS_PER_ASSET]
            raw_preview = table_text
        elif content_type == "image":
            raw_preview = summary or "[image asset]"
        else:
            raw_preview = raw_content[:800]

        return f"""ASSET
source_file: {source_file}
doc_id: {doc_id}
content_type: {content_type}
locator: {locator_text}
summary:
{summary}

content_preview:
{raw_preview}
"""

    def _build_page_label(self, metadata: dict) -> str | None:
        page_number = metadata.get("page_number")
        page_start = metadata.get("page_start")
        page_end = metadata.get("page_end")

        if page_number is not None:
            return f"page {page_number}"

        if page_start is not None and page_end is not None:
            if page_start == page_end:
                return f"page {page_start}"
            return f"pages {page_start}-{page_end}"

        if page_start is not None:
            return f"page {page_start}"

        return None

    def _build_prompt(
        self,
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

    def _parse_generated_entries(self, raw_output: str) -> list[dict]:
        candidate_text = self._extract_json_array(raw_output)

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

            expected_doc_ids = self._normalize_string_list(item.get("expected_doc_ids"))
            expected_sources = self._normalize_string_list(item.get("expected_sources"))

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

    def _extract_json_array(self, raw_output: str) -> str:
        cleaned = raw_output.strip()

        if cleaned.startswith("```"):
            cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned)
            cleaned = re.sub(r"\s*```$", "", cleaned)

        start = cleaned.find("[")
        end = cleaned.rfind("]")

        if start == -1 or end == -1 or end < start:
            raise ValueError("The model response does not contain a JSON array.")

        return cleaned[start : end + 1]

    def _normalize_string_list(self, values) -> list[str]:
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
