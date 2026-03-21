from __future__ import annotations

import json
import re
from typing import Any

from src.core.config import LLM


class GroundednessService:
    """
    Deprecated: use ``LLMJudgeService`` for a single-pass judge with all metrics.

    LLM-as-a-judge groundedness: whether the answer is fully supported by the raw
    retrieval context (not string overlap with expected answers).
    """

    _MAX_CONTEXT_CHARS = 14_000

    def compute_groundedness(
        self,
        *,
        question: str,
        answer: str,
        raw_context: str,
    ) -> float:
        q = (question or "").strip()
        a = (answer or "").strip()
        ctx = (raw_context or "").strip()

        if not a:
            return 0.0

        if len(ctx) > self._MAX_CONTEXT_CHARS:
            ctx = ctx[: self._MAX_CONTEXT_CHARS]

        prompt = f"""You are an expert evaluator for retrieval-augmented QA.

Task: score how well the ASSISTANT ANSWER is grounded in the RETRIEVED CONTEXT only.
- 1.0 = every factual claim in the answer is directly supported by the context (paraphrases OK).
- 0.0 = any important claim is missing from the context, contradicted, or clearly invented.
- Values between 0 and 1 for partial support (use judgment).

Rules:
- Ignore whether the answer is "correct" in the real world; only judge support from the context text.
- Polite refusals ("I don't know") with no unsupported claims score 1.0 if consistent with the context.
- Output a single JSON object, no markdown fences, no extra keys, no commentary.
- Use this exact shape: {{"groundedness_score": <number between 0 and 1>}}

QUESTION:
{q}

RETRIEVED CONTEXT:
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

    def _parse_score(self, text: str) -> float | None:
        cleaned = text.strip()
        if cleaned.startswith("```"):
            cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned, flags=re.IGNORECASE)
            cleaned = re.sub(r"\s*```\s*$", "", cleaned)

        try:
            data: Any = json.loads(cleaned)
            if isinstance(data, dict):
                raw = data.get("groundedness_score")
            else:
                raw = None
            if raw is None:
                return None
            return float(raw)
        except (json.JSONDecodeError, TypeError, ValueError):
            pass

        match = re.search(
            r'"groundedness_score"\s*:\s*([-+]?[0-9]*\.?[0-9]+(?:[eE][-+]?[0-9]+)?)',
            text,
        )
        if match:
            try:
                return float(match.group(1))
            except ValueError:
                return None
        return None
