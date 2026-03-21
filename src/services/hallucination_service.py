from __future__ import annotations

import json
import re
from typing import Any

from src.core.config import LLM


class HallucinationService:
    """
    Deprecated: use ``LLMJudgeService`` for a single-pass judge with all metrics.

    LLM-as-a-judge: detect factual claims in the answer that are not supported by
    the provided context (hallucinations), including partial hallucinations.
    """

    def compute_hallucination(
        self,
        *,
        question: str,
        answer: str,
        raw_context: str,
    ) -> tuple[float, bool]:
        q = (question or "").strip()
        a = (answer or "").strip()
        ctx = (raw_context or "").strip()

        if not a:
            return 1.0, False

        prompt = f"""You are an expert evaluator for retrieval-augmented question answering.

Task: HALLUCINATION DETECTION — decide whether the ASSISTANT ANSWER contains claims
that are NOT supported by the PROVIDED CONTEXT. A partial hallucination (some claims
supported, some not) must still be flagged.

Scoring (hallucination_score):
- 1.0 = every substantive claim in the answer is directly supported by the context (no hallucination).
- 0.0 = the answer is entirely unsupported or contradicts the context (fully hallucinated).
- Use values between 0 and 1 when only part of the answer is supported.

Rules:
- Judge ONLY factual support against PROVIDED CONTEXT, not real-world truth.
- Do NOT reward writing style, length, or politeness.
- Decompose the answer mentally into claims; unsupported or invented claims lower the score.
- If the context is empty or too thin to verify, treat unsupported specifics as hallucination.

Output a single JSON object, no markdown fences, no commentary outside JSON.
Required keys:
- "hallucination_score" (number from 0 to 1; higher = less hallucination / better supported)
- "has_hallucination" (boolean; true if ANY unsupported substantive claim appears)

Optional key: "reason" (short string).

Example: {{"hallucination_score": 0.6, "has_hallucination": true, "reason": "..."}}

USER QUESTION:
{q}

PROVIDED CONTEXT:
{ctx}

ASSISTANT ANSWER:
{a}
""".strip()

        try:
            response = LLM.invoke(prompt)
            text = getattr(response, "content", str(response)).strip()
        except Exception:
            return 0.0, True

        parsed = self._parse_response(text)
        if parsed is None:
            return 0.0, True

        score, has_hall = parsed
        score = round(max(0.0, min(1.0, score)), 2)
        return score, bool(has_hall)

    def _parse_response(self, text: str) -> tuple[float, bool] | None:
        cleaned = text.strip()
        if cleaned.startswith("```"):
            cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned, flags=re.IGNORECASE)
            cleaned = re.sub(r"\s*```\s*$", "", cleaned)

        data: Any
        try:
            data = json.loads(cleaned)
        except json.JSONDecodeError:
            data = None

        if not isinstance(data, dict):
            score = self._regex_float(text, r'"hallucination_score"\s*:\s*([-+]?[0-9]*\.?[0-9]+(?:[eE][-+]?[0-9]+)?)')
            if score is None:
                return None
            flag = self._regex_bool(text, r'"has_hallucination"\s*:\s*(true|false)')
            has_hall = flag if flag is not None else score < 1.0
            return score, has_hall

        raw_score = data.get("hallucination_score")
        if raw_score is None:
            return None
        try:
            score = float(raw_score)
        except (TypeError, ValueError):
            return None

        raw_flag = data.get("has_hallucination")
        if isinstance(raw_flag, bool):
            has_hall = raw_flag
        elif raw_flag is None:
            has_hall = score < 1.0
        elif isinstance(raw_flag, str):
            has_hall = raw_flag.strip().lower() in {"true", "1", "yes"}
        else:
            has_hall = bool(raw_flag)

        return score, has_hall

    def _regex_float(self, text: str, pattern: str) -> float | None:
        match = re.search(pattern, text)
        if not match:
            return None
        try:
            return float(match.group(1))
        except ValueError:
            return None

    def _regex_bool(self, text: str, pattern: str) -> bool | None:
        match = re.search(pattern, text, flags=re.IGNORECASE)
        if not match:
            return None
        return match.group(1).lower() == "true"
