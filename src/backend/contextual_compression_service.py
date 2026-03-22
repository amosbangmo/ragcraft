"""
Heuristic contextual compression for retrieved assets before prompt assembly.

Text: keep sentences that share lexical overlap with the query (same tokenization
style as reranking). Tables unchanged. Images: drop raw payload; summary remains.
"""

from __future__ import annotations

import re


_KEYWORD_RE = re.compile(r"[a-zA-Z0-9_/-]+")


def _tokenize_keywords(text: str) -> set[str]:
    return {t.lower() for t in _KEYWORD_RE.findall(text or "") if len(t) > 1}


def _split_sentences(text: str) -> list[str]:
    text = (text or "").strip()
    if not text:
        return []

    sentences: list[str] = []
    for para in re.split(r"\n{2,}", text):
        para = para.strip()
        if not para:
            continue
        for part in re.split(r"(?<=[.!?…\u3002])\s+", para):
            p = part.strip()
            if p:
                sentences.append(p)

    return sentences if sentences else [text]


def _asset_prompt_chars(asset: dict) -> int:
    """Approximate prompt-facing character footprint (aligned with PromptBuilderService)."""
    ct = asset.get("content_type", "unknown")
    raw = asset.get("raw_content", "") or ""
    summary = asset.get("summary", "") or ""
    meta = asset.get("metadata", {}) or {}

    if ct == "text":
        return len(raw)
    if ct == "table":
        return len(raw) + len(meta.get("table_text") or "")
    if ct == "image":
        return len(summary)
    return len(raw)


class ContextualCompressionService:
    def prompt_char_estimate(self, assets: list[dict]) -> int:
        return sum(_asset_prompt_chars(a) for a in assets)

    def compress(self, *, query: str, assets: list[dict]) -> list[dict]:
        if not assets:
            return []

        q_kw = _tokenize_keywords(query)
        return [self._compress_asset(asset, q_kw) for asset in assets]

    def _compress_asset(self, asset: dict, q_kw: set[str]) -> dict:
        meta = asset.get("metadata") or {}
        out = {
            **asset,
            "metadata": dict(meta) if isinstance(meta, dict) else {},
        }
        ct = out.get("content_type", "unknown")

        if ct == "text":
            raw = out.get("raw_content") or ""
            out["raw_content"] = self._compress_text(raw, q_kw)
        elif ct == "image":
            out["raw_content"] = ""

        return out

    def _compress_text(self, text: str, q_kw: set[str]) -> str:
        if not (text or "").strip():
            return text
        if not q_kw:
            return text

        sentences = _split_sentences(text)
        if len(sentences) == 1:
            if _tokenize_keywords(sentences[0]) & q_kw:
                return sentences[0]
            return text

        kept = [s for s in sentences if _tokenize_keywords(s) & q_kw]
        if not kept:
            return text
        return "\n\n".join(kept)
