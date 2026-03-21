from __future__ import annotations

import json
import re
from typing import Any

from src.core.config import LLM


class CitationFaithfulnessService:
    """
    Deprecated: use ``LLMJudgeService`` for a single-pass judge with all metrics.

    LLM-as-a-judge: whether cited sources actually support the claims made in the
    answer (not whether citations match a gold label set).
    """

    _MAX_CONTEXT_CHARS = 14_000
    _MAX_REF_JSON_CHARS = 8_000

    def compute_citation_faithfulness(
        self,
        *,
        question: str,
        answer: str,
        source_references: list[dict],
        raw_context: str,
    ) -> float:
        q = (question or "").strip()
        a = (answer or "").strip()
        ctx = (raw_context or "").strip()

        if not a:
            return 0.0

        if len(ctx) > self._MAX_CONTEXT_CHARS:
            ctx = ctx[: self._MAX_CONTEXT_CHARS]

        refs_json = self._format_source_references(source_references)

        prompt = f"""You are an expert evaluator for retrieval-augmented QA.

Task: score CITATION FAITHFULNESS — do the SOURCE REFERENCES (and the evidence they
point to in the raw context) actually support the factual claims in the ASSISTANT ANSWER?
- 1.0 = essentially every substantive claim in the answer is well supported by the cited material / context.
- 0.0 = important claims are unsupported, contradicted, or the citations do not back what the answer says.
- Use values between 0 and 1 for partial alignment.

Rules:
- Judge alignment between the answer and what the citations/context justify, not real-world correctness.
- If there are no source references, score based on whether the answer stays faithful to the raw context only.
- Polite refusals with no unsupported claims can score 1.0 if consistent with the context.
- Output a single JSON object, no markdown fences, no commentary outside JSON.
- Required key: "citation_faithfulness_score" (number from 0 to 1).
- Optional key: "reason" (short string).

Example shape: {{"citation_faithfulness_score": 0.84, "reason": "..."}}

QUESTION:
{q}

SOURCE REFERENCES (JSON):
{refs_json}

RAW RETRIEVED CONTEXT:
{ctx}

ASSISTANT ANSWER:
{a}
""".strip()

        try:
            response = LLM.invoke(prompt)
            text = getattr(response, "content", str(response)).strip()
        except Exception:
            return 0.0

        score = self._parse_score(text)
        if score is None:
            return 0.0

        return round(max(0.0, min(1.0, score)), 2)

    def _format_source_references(self, source_references: list[dict]) -> str:
        refs = source_references if isinstance(source_references, list) else []
        try:
            text = json.dumps(refs, ensure_ascii=False, indent=2)
        except (TypeError, ValueError):
            text = "[]"
        if len(text) > self._MAX_REF_JSON_CHARS:
            return text[: self._MAX_REF_JSON_CHARS] + "\n... (truncated)"
        return text

    def _parse_score(self, text: str) -> float | None:
        cleaned = text.strip()
        if cleaned.startswith("```"):
            cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned, flags=re.IGNORECASE)
            cleaned = re.sub(r"\s*```\s*$", "", cleaned)

        try:
            data: Any = json.loads(cleaned)
            if isinstance(data, dict):
                raw = data.get("citation_faithfulness_score")
            else:
                raw = None
            if raw is None:
                return None
            return float(raw)
        except (json.JSONDecodeError, TypeError, ValueError):
            pass

        match = re.search(
            r'"citation_faithfulness_score"\s*:\s*([-+]?[0-9]*\.?[0-9]+(?:[eE][-+]?[0-9]+)?)',
            text,
        )
        if match:
            try:
                return float(match.group(1))
            except ValueError:
                return None
        return None
