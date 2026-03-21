from __future__ import annotations

import json
import re
from typing import Any

from src.core.config import LLM


class AnswerRelevanceService:
    """
    Deprecated: use ``LLMJudgeService`` for a single-pass judge with all metrics.

    LLM-as-a-judge: how well the answer addresses the user's question (coverage,
    focus, usefulness), independent of factual correctness or retrieval grounding.
    """

    def compute_answer_relevance(
        self,
        *,
        question: str,
        answer: str,
    ) -> float:
        q = (question or "").strip()
        a = (answer or "").strip()

        if not a:
            return 0.0

        prompt = f"""You are an expert evaluator for question answering.

Task: score ANSWER RELEVANCE — how well the ASSISTANT ANSWER addresses the USER QUESTION.
Judge coverage of what was asked, whether the answer stays on topic, and how useful it is
to someone who asked that question. Do NOT score factual correctness against the real world.

Scoring:
- 1.0 = directly addresses the question, appropriate scope, clearly useful.
- 0.0 = mostly off-topic, ignores the question, or dominated by irrelevant content.
- Use values between 0 and 1 for partial relevance.

Rules:
- Ignore whether claims are true; only judge alignment with the question and usefulness.
- Polite refusals ("I don't know") score high only if they appropriately respond to the question.
- Output a single JSON object, no markdown fences, no commentary outside JSON.
- Required key: "answer_relevance_score" (number from 0 to 1).
- Optional key: "reason" (short string).

Example shape: {{"answer_relevance_score": 0.88, "reason": "..."}}

USER QUESTION:
{q}

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
                raw = data.get("answer_relevance_score")
            else:
                raw = None
            if raw is None:
                return None
            return float(raw)
        except (json.JSONDecodeError, TypeError, ValueError):
            pass

        match = re.search(
            r'"answer_relevance_score"\s*:\s*([-+]?[0-9]*\.?[0-9]+(?:[eE][-+]?[0-9]+)?)',
            text,
        )
        if match:
            try:
                return float(match.group(1))
            except ValueError:
                return None
        return None
