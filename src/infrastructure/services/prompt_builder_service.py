from src.domain.prompt_source import PromptSource
from src.infrastructure.services.image_context_service import ImageContextService
from src.infrastructure.services.layout_context_service import describe_layout_group


_MAX_STRUCTURED_TABLE_ROWS = 14
_MAX_STRUCTURED_CELL_CHARS = 88


class PromptBuilderService:
    def __init__(
        self,
        *,
        max_text_chars_per_asset: int,
        max_table_chars_per_asset: int,
        image_context_service: ImageContextService | None = None,
    ):
        self.max_text_chars_per_asset = max_text_chars_per_asset
        self.max_table_chars_per_asset = max_table_chars_per_asset
        self._max_structured_block_chars = min(2800, max(400, max_table_chars_per_asset))
        self._image_context = image_context_service or ImageContextService()

    def prepare_image_contexts(
        self,
        raw_assets: list[dict],
    ) -> tuple[dict[str, dict], bool]:
        """
        Precompute per-image context dicts (metadata + optional same-page / pool neighbors).
        Returns (map doc_id -> context, any_image_used_enriched_signals).
        """
        by_id: dict[str, dict] = {}
        any_enriched = False
        for asset in raw_assets:
            if asset.get("content_type") != "image":
                continue
            doc_id = asset.get("doc_id")
            if not doc_id:
                continue
            neighbors = self._image_context.find_text_neighbors(asset, raw_assets)
            ctx = self._image_context.build_context(asset, neighbors)
            by_id[str(doc_id)] = ctx
            if self._image_context.is_context_enriched(ctx):
                any_enriched = True
        return by_id, any_enriched

    def _layout_type_label(self, content_type: str) -> str:
        if content_type == "text":
            return "Text"
        if content_type == "table":
            return "Table"
        if content_type == "image":
            return "Figure"
        return content_type[:1].upper() + content_type[1:] if content_type else "Asset"

    def build_raw_context(
        self,
        *,
        raw_assets: list[dict],
        prompt_sources: list[PromptSource],
        image_context_by_doc_id: dict[str, dict] | None = None,
        asset_groups: list[list[dict]] | None = None,
        max_text_chars_per_asset: int | None = None,
        max_table_chars_per_asset: int | None = None,
    ) -> str:
        """``raw_assets`` may be context-compressed upstream before this call."""
        text_lim = (
            self.max_text_chars_per_asset
            if max_text_chars_per_asset is None
            else int(max_text_chars_per_asset)
        )
        table_lim = (
            self.max_table_chars_per_asset
            if max_table_chars_per_asset is None
            else int(max_table_chars_per_asset)
        )
        structured_budget = min(2800, max(400, table_lim))

        if image_context_by_doc_id is None:
            image_context_by_doc_id, _ = self.prepare_image_contexts(raw_assets)
        prompt_source_by_id = {
            id(asset): ps for asset, ps in zip(raw_assets, prompt_sources, strict=True)
        }

        def format_one(asset: dict, *, layout_mode: bool) -> str:
            ps = prompt_source_by_id[id(asset)]
            img_ctx = (
                image_context_by_doc_id.get(str(asset.get("doc_id")))
                if asset.get("content_type") == "image" and asset.get("doc_id")
                else None
            )
            body = self._format_raw_asset_for_prompt(
                asset=asset,
                prompt_source=ps,
                image_context=img_ctx,
                max_text_chars=text_lim,
                max_table_chars=table_lim,
                structured_table_budget=structured_budget,
            )
            if layout_mode:
                tag = self._layout_type_label(str(asset.get("content_type") or "unknown"))
                return f"[{tag}]\n{body}"
            return body

        if not asset_groups:
            return "\n\n".join(format_one(a, layout_mode=False) for a in raw_assets)

        parts: list[str] = []
        for group in asset_groups:
            header = describe_layout_group(group)
            inner = "\n\n".join(format_one(a, layout_mode=True) for a in group)
            parts.append(f"=== {header} ===\nRelated assets (same area of the document; use order and proximity):\n\n{inner}")
        return "\n\n".join(parts)

    def build_prompt(
        self,
        *,
        question: str,
        chat_history: list[str],
        raw_context: str,
        table_aware_instruction: str | None = None,
        orchestration_hint: str | None = None,
        layout_aware: bool = False,
    ) -> str:
        history_text = "\n".join(chat_history) if chat_history else "No prior chat history."

        table_block = ""
        if table_aware_instruction and table_aware_instruction.strip():
            table_block = f"\n{table_aware_instruction.strip()}\n"

        orchestration_block = ""
        if orchestration_hint and orchestration_hint.strip():
            orchestration_block = f"\nMultimodal orchestration:\n{orchestration_hint.strip()}\n"

        layout_block = ""
        if layout_aware:
            layout_block = """
- Context is grouped by document layout (page / section / proximity). Assets under the same heading are neighbors in the source—use relationships between them.
- Use nearby text to interpret tables and images; use tables/images to ground narrative text in the same group.
"""

        return f"""
You are an AI assistant answering questions using only the provided raw multimodal context.

Chat history:
{history_text}

Question:
{question}

Raw multimodal context:
{raw_context}
{table_block}{orchestration_block}
Instructions:
- Use only the provided raw context.
- Retrieval happened in two stages:
  1. large recall retrieval over summary documents
  2. strict reranking over rehydrated raw assets
- Only the final reranked assets are included in the context.
- If the answer is not supported by the raw context, say you don't know.
- Be precise and concise.
- Every factual claim grounded in a source should include its prompt source label.
- Use the exact prompt source labels provided in each asset block.
- Prompt source references must be inline, for example:
  - [Source 1]
  - [Source 2][Table: Table 2]
  - [Source 3][Figure: Attention map]
- When useful, mention whether the evidence came from text, table, or figure assets.
- For figure assets, rely only on metadata, contextual text blocks, and the image retrieval summary; you cannot see pixels—do not invent visual details.
- When citing figure evidence, say so explicitly (e.g. "per figure metadata / surrounding text / retrieval summary for [Source N]").
- For table assets, when a structured table excerpt is provided, read values from it first for comparisons, rankings, and numeric facts; cross-check the raw table if needed.
- Never invent document content that is not explicitly present in the raw context.{layout_block}
""".strip()

    def _truncate_cell(self, value: object, max_chars: int = _MAX_STRUCTURED_CELL_CHARS) -> str:
        s = " ".join(str(value or "").split())
        if len(s) <= max_chars:
            return s
        return s[: max_chars - 1] + "…"

    def _format_structured_table_excerpt(
        self,
        structured: dict,
        *,
        budget: int | None = None,
    ) -> str:
        headers = list(structured.get("headers") or [])
        rows = list(structured.get("rows") or [])
        if not headers and not rows:
            return ""

        use_budget = self._max_structured_block_chars if budget is None else int(budget)
        lines: list[str] = []
        used = 0

        def consume(line: str) -> bool:
            nonlocal used
            need = len(line) + (1 if lines else 0)
            if used + need > use_budget:
                return False
            lines.append(line)
            used += need
            return True

        intro = (
            "Use this structured excerpt for comparisons, min/max, rankings, and exact numeric values. "
            "If a cell is unclear, fall back to the raw HTML/text below."
        )
        if not consume(intro):
            return ""

        ncol = max(len(headers), max((len(r) for r in rows), default=0))
        two_col_kv = (
            ncol == 2
            and rows
            and all(len(r) >= 2 for r in rows[:_MAX_STRUCTURED_TABLE_ROWS])
        )

        if headers:
            hdr_line = "Column headers: " + " | ".join(
                self._truncate_cell(h) for h in headers
            )
            consume(hdr_line)

        if two_col_kv:
            consume("Two-column layout (treat as attribute → value when applicable):")
            for row in rows[:_MAX_STRUCTURED_TABLE_ROWS]:
                left, right = row[0], row[1]
                row_line = f"  {self._truncate_cell(left)} → {self._truncate_cell(right)}"
                if not consume(row_line):
                    break
        else:
            consume("Data rows (pipe-separated cells, aligned to headers left-to-right):")
            for row in rows[:_MAX_STRUCTURED_TABLE_ROWS]:
                cells = list(row)
                while len(cells) < ncol:
                    cells.append("")
                if ncol:
                    cells = cells[:ncol]
                row_line = "  " + " | ".join(self._truncate_cell(c) for c in cells)
                if not consume(row_line):
                    break

        if len(rows) > _MAX_STRUCTURED_TABLE_ROWS:
            consume(f"… ({len(rows) - _MAX_STRUCTURED_TABLE_ROWS} additional rows omitted)")

        return "\n".join(lines)

    def _format_raw_asset_for_prompt(
        self,
        *,
        asset: dict,
        prompt_source: PromptSource,
        image_context: dict | None = None,
        max_text_chars: int | None = None,
        max_table_chars: int | None = None,
        structured_table_budget: int | None = None,
    ) -> str:
        content_type = asset.get("content_type", "unknown")
        source_file = asset.get("source_file", "unknown")
        raw_content = asset.get("raw_content", "") or ""
        metadata = asset.get("metadata", {}) or {}
        summary = asset.get("summary", "") or ""
        doc_id = asset.get("doc_id", "?")
        prompt_source_label = prompt_source.prompt_label
        text_limit = (
            self.max_text_chars_per_asset if max_text_chars is None else int(max_text_chars)
        )
        table_limit = (
            self.max_table_chars_per_asset if max_table_chars is None else int(max_table_chars)
        )

        if content_type == "text":
            trimmed = raw_content[:text_limit]
            return f"""Asset {prompt_source.source_number}
Prompt source: {prompt_source_label}
Type: text
Doc ID: {doc_id}
Source file: {source_file}
Metadata: {metadata}

Raw text:
{trimmed}
"""

        if content_type == "table":
            table_title = metadata.get("table_title")
            table_text = metadata.get("table_text") or ""
            structured = metadata.get("structured_table") or {}
            has_structured = bool(structured.get("rows") or structured.get("headers"))
            excerpt = (
                self._format_structured_table_excerpt(structured)
                if has_structured
                else ""
            ).strip()
            meta_for_prompt = {
                k: v for k, v in (metadata or {}).items() if k != "structured_table"
            }
            if excerpt:
                meta_for_prompt["structured_table"] = "(see Structured table excerpt below)"

            structured_block = ""
            if excerpt:
                structured_block = f"""
Structured table excerpt:
{excerpt}

Structured reasoning notes:
- Compare values within the same column or row only when the headers make that meaningful.
- For min, max, ranking, or totals, derive answers only from values shown in the excerpt or raw table; do not extrapolate missing cells.
"""

            return f"""Asset {prompt_source.source_number}
Prompt source: {prompt_source_label}
Type: table
Doc ID: {doc_id}
Source file: {source_file}
Metadata: {meta_for_prompt}

Table title:
{table_title}
{structured_block}
Raw table HTML:
{raw_content[:table_limit]}

Raw table text:
{table_text[:table_limit]}
"""

        if content_type == "image":
            meta_for_prompt = {
                "page_number": metadata.get("page_number"),
                "page_start": metadata.get("page_start"),
                "page_end": metadata.get("page_end"),
                "image_index": metadata.get("image_index"),
                "image_mime_type": metadata.get("image_mime_type"),
                "element_category": metadata.get("element_category"),
                "embedded_path": metadata.get("embedded_path"),
                "rerank_score": metadata.get("rerank_score"),
            }

            if image_context is None:
                neighbors = self._image_context.find_text_neighbors(asset, [asset])
                image_context = self._image_context.build_context(asset, neighbors)

            title_line = image_context.get("image_title") or metadata.get("image_title") or "(none)"
            page_line = image_context.get("page_context") or "(unknown)"
            ctx_summary = image_context.get("contextual_summary") or ""
            surrounding = image_context.get("surrounding_text")
            neighbor_block = image_context.get("neighbor_text")

            extra_blocks = ""
            if surrounding:
                extra_blocks += f"""
Same-page text excerpt (from extraction, not a vision read):
{surrounding}
"""
            if neighbor_block:
                extra_blocks += f"""
Nearby retrieved text chunks (same document; use for grounding only):
{neighbor_block}
"""
            if ctx_summary:
                extra_blocks += f"""
Contextual signals (for orientation):
{ctx_summary}
"""

            return f"""Asset {prompt_source.source_number}
Prompt source: {prompt_source_label}
Type: image
Doc ID: {doc_id}
Source file: {source_file}
Structural metadata: {meta_for_prompt}
Image title / caption signal: {title_line}
Page context: {page_line}
{extra_blocks.strip()}

Image retrieval summary:
{summary}

Raw image:
[Binary image asset stored in SQLite as base64 and intentionally omitted from this final prompt.]
"""

        trimmed = raw_content[:2000]
        return f"""Asset {prompt_source.source_number}
Prompt source: {prompt_source_label}
Type: {content_type}
Doc ID: {doc_id}
Source file: {source_file}
Metadata: {metadata}

Raw content:
{trimmed}
"""
