"""
Build compact, non-visual context for image assets (metadata + nearby text).
"""

from __future__ import annotations

_MAX_NEIGHBORS = 3
_MAX_CHARS_PER_NEIGHBOR = 380
_MAX_NEIGHBOR_BLOCK_CHARS = 900
_MAX_SURROUNDING_PROMPT_CHARS = 420


def _norm_source(asset: dict, metadata: dict) -> str | None:
    for key in ("source_file", "file_name"):
        v = asset.get(key) or metadata.get(key)
        if v is not None:
            s = str(v).strip()
            if s:
                return s
    return None


def _image_page_span(metadata: dict) -> tuple[int, int] | None:
    pn = metadata.get("page_number")
    if pn is None:
        return None
    try:
        p = int(pn)
    except (TypeError, ValueError):
        return None
    return p, p


def _text_page_span(metadata: dict) -> tuple[int, int] | None:
    ps, pe = metadata.get("page_start"), metadata.get("page_end")
    if ps is not None and pe is not None:
        try:
            a, b = int(ps), int(pe)
        except (TypeError, ValueError):
            return None
        lo, hi = (a, b) if a <= b else (b, a)
        return lo, hi
    return None


def _spans_overlap(a: tuple[int, int], b: tuple[int, int]) -> bool:
    return not (a[1] < b[0] or b[1] < a[0])


class ImageContextService:
    def build_context(self, asset: dict, neighbors: list[dict]) -> dict:
        metadata = asset.get("metadata") or {}
        image_title = metadata.get("image_title")
        if image_title is not None:
            image_title = str(image_title).strip() or None

        page_context = self._format_page_context(metadata)
        surrounding = metadata.get("surrounding_text")
        if isinstance(surrounding, str):
            surrounding = surrounding.strip() or None
            if surrounding and len(surrounding) > _MAX_SURROUNDING_PROMPT_CHARS:
                surrounding = surrounding[: _MAX_SURROUNDING_PROMPT_CHARS - 1] + "…"
        else:
            surrounding = None

        neighbor_text = self._format_neighbor_block(neighbors)

        summary_bits: list[str] = []
        if page_context:
            summary_bits.append(page_context)
        if image_title:
            summary_bits.append(f"title/caption signal: {image_title}")
        if surrounding:
            summary_bits.append("surrounding text excerpt available")
        if neighbor_text:
            summary_bits.append("nearby retrieved text available")
        contextual_summary = "; ".join(summary_bits) if summary_bits else None

        return {
            "image_title": image_title,
            "page_context": page_context,
            "neighbor_text": neighbor_text,
            "surrounding_text": surrounding,
            "contextual_summary": contextual_summary,
        }

    def is_context_enriched(self, context: dict) -> bool:
        if (context.get("surrounding_text") or "").strip():
            return True
        if (context.get("neighbor_text") or "").strip():
            return True
        return False

    def find_text_neighbors(
        self,
        image_asset: dict,
        pool: list[dict],
        *,
        max_neighbors: int = _MAX_NEIGHBORS,
    ) -> list[dict]:
        img_meta = image_asset.get("metadata") or {}
        src = _norm_source(image_asset, img_meta)
        if not src:
            return []

        img_span = _image_page_span(img_meta)

        scored: list[tuple[int, int, dict]] = []
        for idx, other in enumerate(pool):
            if other is image_asset:
                continue
            if other.get("content_type") != "text":
                continue
            om = other.get("metadata") or {}
            if _norm_source(other, om) != src:
                continue

            txt_span = _text_page_span(om)
            if img_span is not None:
                if txt_span is None:
                    continue
                if not _spans_overlap(img_span, txt_span):
                    continue
                overlap_lo = max(img_span[0], txt_span[0])
                overlap_hi = min(img_span[1], txt_span[1])
                overlap = overlap_hi - overlap_lo + 1 if overlap_hi >= overlap_lo else 0
            else:
                # Embedded / unpaged images: same-file text neighbors only (weak signal).
                overlap = 0

            raw = (other.get("raw_content") or "").strip()
            if not raw:
                raw = (other.get("summary") or "").strip()
            if not raw:
                continue

            scored.append((overlap, -idx, other))

        scored.sort(key=lambda t: (-t[0], t[1]))
        return [item[2] for item in scored[:max_neighbors]]

    def _format_page_context(self, metadata: dict) -> str | None:
        pn = metadata.get("page_number")
        if pn is not None:
            try:
                return f"Page {int(pn)}"
            except (TypeError, ValueError):
                return f"Page {pn}"
        ps, pe = metadata.get("page_start"), metadata.get("page_end")
        if ps is not None and pe is not None:
            try:
                a, b = int(ps), int(pe)
            except (TypeError, ValueError):
                return None
            lo, hi = (a, b) if a <= b else (b, a)
            if lo == hi:
                return f"Page {lo}"
            return f"Pages {lo}–{hi}"
        return None

    def _format_neighbor_block(self, neighbors: list[dict]) -> str | None:
        if not neighbors:
            return None
        lines: list[str] = []
        used = 0
        for i, n in enumerate(neighbors, start=1):
            text = (n.get("raw_content") or n.get("summary") or "").strip()
            text = " ".join(text.split())
            if len(text) > _MAX_CHARS_PER_NEIGHBOR:
                text = text[: _MAX_CHARS_PER_NEIGHBOR - 1] + "…"
            line = f"[{i}] {text}"
            need = len(line) + (1 if lines else 0)
            if used + need > _MAX_NEIGHBOR_BLOCK_CHARS:
                break
            lines.append(line)
            used += need
        return "\n".join(lines) if lines else None
