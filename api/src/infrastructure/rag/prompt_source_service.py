from domain.rag.prompt_source import PromptSource


class PromptSourceService:
    def build_prompt_sources(self, raw_assets: list[dict]) -> list[PromptSource]:
        prompt_sources: list[PromptSource] = []

        for index, asset in enumerate(raw_assets, start=1):
            metadata = asset.get("metadata", {}) or {}
            content_type = asset.get("content_type", "unknown")
            source_file = asset.get("source_file", "unknown")
            doc_id = asset.get("doc_id", "")

            page_label = self._build_page_label(metadata)
            section_label = self._build_section_label(metadata)
            locator_label = self._build_locator_label(content_type, metadata)
            display_label = self._build_display_label(
                source_number=index,
                source_file=source_file,
                section_label=section_label,
                page_label=page_label,
                locator_label=locator_label,
            )
            prompt_label = self._build_prompt_label(
                source_number=index,
                section_label=section_label,
                page_label=page_label,
                locator_label=locator_label,
            )

            prompt_sources.append(
                PromptSource(
                    source_number=index,
                    doc_id=doc_id,
                    source_file=source_file,
                    content_type=content_type,
                    page_label=page_label,
                    locator_label=locator_label,
                    display_label=display_label,
                    prompt_label=prompt_label,
                    metadata=metadata,
                )
            )

        return prompt_sources

    def _build_page_label(self, metadata: dict) -> str | None:
        page_number = metadata.get("page_number")
        page_start = metadata.get("page_start")
        page_end = metadata.get("page_end")

        if page_number is not None:
            return f"Page {page_number}"

        if page_start is not None and page_end is not None:
            if page_start == page_end:
                return f"Page {page_start}"
            return f"Pages {page_start}-{page_end}"

        if page_start is not None:
            return f"Page {page_start}"

        return None

    def _build_section_label(self, metadata: dict) -> str | None:
        for key in ("chunk_title", "section_title"):
            raw = metadata.get(key)
            if raw is None:
                continue
            s = str(raw).strip()
            if s:
                return s[:160] if len(s) > 160 else s
        return None

    def _build_locator_label(self, content_type: str, metadata: dict) -> str | None:
        if content_type == "text":
            start_idx = metadata.get("start_element_index")
            end_idx = metadata.get("end_element_index")

            if start_idx is not None and end_idx is not None:
                if start_idx == end_idx:
                    return f"Element {start_idx}"
                return f"Elements {start_idx}-{end_idx}"

            return None

        if content_type == "table":
            table_title = metadata.get("table_title")
            if table_title:
                return f"Table: {table_title}"
            return "Table"

        if content_type == "image":
            image_title = metadata.get("image_title")
            if image_title:
                return f"Figure: {image_title}"
            return "Figure"

        return None

    def _build_display_label(
        self,
        *,
        source_number: int,
        source_file: str,
        section_label: str | None,
        page_label: str | None,
        locator_label: str | None,
    ) -> str:
        parts = [f"Source {source_number}", source_file]

        if section_label:
            parts.append(f"Section: {section_label}")

        if locator_label:
            parts.append(locator_label)

        if page_label:
            parts.append(page_label)

        return " — ".join(parts)

    def _build_prompt_label(
        self,
        *,
        source_number: int,
        section_label: str | None,
        page_label: str | None,
        locator_label: str | None,
    ) -> str:
        parts = [f"[Source {source_number}]"]

        if section_label:
            parts.append(f"[Section: {section_label}]")

        if page_label:
            parts.append(f"[{page_label}]")

        if locator_label:
            parts.append(f"[{locator_label}]")

        return "".join(parts)
