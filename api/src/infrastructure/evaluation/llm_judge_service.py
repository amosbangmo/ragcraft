from __future__ import annotations

import json
import re
from typing import Any

from infrastructure.config.config import LLM
from domain.evaluation.llm_judge_constants import JUDGE_FAILURE_REASON
from domain.evaluation.llm_judge_result import LLMJudgeResult


class LLMJudgeService:
    """
    Single LLM-as-a-judge pass: groundedness, answer relevance,
    and hallucination signals in one structured JSON response.
    """

    # When ``has_hallucination`` is missing from the model output, infer from
    # ``hallucination_score`` (higher = less hallucination), aligned with
    # failure-analysis thresholds (e.g. DEFAULT_HALLUCINATION_THRESHOLD).
    _HAS_HALLUCINATION_SCORE_FALLBACK_THRESHOLD = 0.5

    _MAX_CONTEXT_CHARS = 14_000
    _MAX_REF_JSON_CHARS = 8_000

    _FLOAT_RE = r"([-+]?[0-9]*\.?[0-9]+(?:[eE][-+]?[0-9]+)?)"

    @staticmethod
    def _failure_result() -> LLMJudgeResult:
        """Used when the LLM call fails or the response is unusable."""
        return LLMJudgeResult(
            groundedness_score=0.0,
            citation_faithfulness_score=0.0,
            answer_relevance_score=0.0,
            hallucination_score=0.0,
            has_hallucination=True,
            answer_correctness_score=0.0,
            reason=JUDGE_FAILURE_REASON,
        )

    @staticmethod
    def _empty_answer_result() -> LLMJudgeResult:
        """No assistant text: skip the LLM; align with prior per-metric stubs."""
        return LLMJudgeResult(
            groundedness_score=0.0,
            citation_faithfulness_score=0.0,
            answer_relevance_score=0.0,
            hallucination_score=1.0,
            has_hallucination=False,
            answer_correctness_score=0.0,
            reason=None,
        )

    def evaluate(
        self,
        *,
        question: str,
        answer: str,
        raw_context: str,
        prompt_sources: list[dict],
        expected_answer: str | None = None,
    ) -> LLMJudgeResult:
        a = (answer or "").strip()
        if not a:
            return self._empty_answer_result()

        q = (question or "").strip()
        ctx = (raw_context or "").strip()
        if len(ctx) > self._MAX_CONTEXT_CHARS:
            ctx = ctx[: self._MAX_CONTEXT_CHARS]

        refs_json = self._format_prompt_sources(prompt_sources)
        gold = (expected_answer or "").strip()
        gold_block = ""
        if gold:
            gold_block = f"""
EXPECTED ANSWER (gold reference, optional alignment target):
{gold}
""".rstrip()

        prompt = f"""You are an expert evaluator for retrieval-augmented question answering.
Evaluate the ASSISTANT ANSWER in one pass and output ONE JSON object only (no markdown, no code fences, no text outside JSON).

Each score must be a number in [0, 1].

Metrics:
- groundedness_score: Are factual claims in the answer supported by RETRIEVED CONTEXT only (paraphrases OK)? Ignore real-world truth beyond the context.
- citation_faithfulness_score: Do inline source citations ([Source N]) align with the claims they support—only citing when the context backs the statement? 1.0 = citations used faithfully; 0.0 = mismatched or misleading citations.
- answer_relevance_score: Does the answer address the USER QUESTION (coverage, focus, usefulness)? Do not score factual correctness against the real world.
- hallucination_score: Higher = less hallucination / better supported by context. 1.0 = no unsupported substantive claims; 0.0 = fully unsupported vs context.
- answer_correctness_score: Holistic factual correctness and completeness of the answer for the USER QUESTION, using RETRIEVED CONTEXT as primary evidence. If EXPECTED ANSWER is provided, also reward alignment with it (paraphrases and equivalent meaning OK). 1.0 = fully correct and complete; 0.0 = incorrect or missing key facts.
- has_hallucination: true if ANY substantive claim is not supported by the provided context.
- reason: short string explaining the scores (optional but preferred).

Required keys: groundedness_score, citation_faithfulness_score, answer_relevance_score, hallucination_score, answer_correctness_score, has_hallucination, reason.

USER QUESTION:
{q}
{gold_block}

PROMPT SOURCES (JSON):
{refs_json}

RETRIEVED CONTEXT:
{ctx}

ASSISTANT ANSWER:
{a}
""".strip()

        try:
            response = LLM.invoke(prompt)
            text = getattr(response, "content", str(response)).strip()
        except Exception:
            return self._failure_result()

        parsed = self._parse_response(text)
        if parsed is None:
            return self._failure_result()

        g, cf, r, h, ac, flag, reason = parsed
        return LLMJudgeResult(
            groundedness_score=round(g, 2),
            citation_faithfulness_score=round(cf, 2),
            answer_relevance_score=round(r, 2),
            hallucination_score=round(h, 2),
            has_hallucination=flag,
            answer_correctness_score=round(ac, 2),
            reason=reason,
        )

    def _format_prompt_sources(self, prompt_sources: list[dict]) -> str:
        refs = prompt_sources if isinstance(prompt_sources, list) else []
        try:
            text = json.dumps(refs, ensure_ascii=False, indent=2)
        except (TypeError, ValueError):
            text = "[]"
        if len(text) > self._MAX_REF_JSON_CHARS:
            return text[: self._MAX_REF_JSON_CHARS] + "\n... (truncated)"
        return text

    def _parse_response(self, text: str) -> tuple[float, float, float, float, float, bool, str | None] | None:
        cleaned = text.strip()
        if cleaned.startswith("```"):
            cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned, flags=re.IGNORECASE)
            cleaned = re.sub(r"\s*```\s*$", "", cleaned)

        data: Any = None
        try:
            data = json.loads(cleaned)
        except json.JSONDecodeError:
            data = None

        if isinstance(data, dict):
            g = self._read_score(data, "groundedness_score", text)
            cf = self._read_score(data, "citation_faithfulness_score", text)
            r = self._read_score(data, "answer_relevance_score", text)
            h = self._read_score(data, "hallucination_score", text)
            ac = self._read_score(data, "answer_correctness_score", text)
            if g is None and cf is None and r is None and h is None and ac is None:
                return None
            g = 0.0 if g is None else self._clamp01(g)
            cf = g if cf is None else self._clamp01(cf)
            r = 0.0 if r is None else self._clamp01(r)
            h = 0.0 if h is None else self._clamp01(h)
            ac = 0.0 if ac is None else self._clamp01(ac)
            flag = self._read_bool(data, text, h)
            reason = self._read_reason(data)
            return g, cf, r, h, ac, flag, reason

        g = self._regex_float(text, r'"groundedness_score"\s*:\s*' + self._FLOAT_RE)
        cf = self._regex_float(text, r'"citation_faithfulness_score"\s*:\s*' + self._FLOAT_RE)
        r = self._regex_float(text, r'"answer_relevance_score"\s*:\s*' + self._FLOAT_RE)
        h = self._regex_float(text, r'"hallucination_score"\s*:\s*' + self._FLOAT_RE)
        ac = self._regex_float(text, r'"answer_correctness_score"\s*:\s*' + self._FLOAT_RE)
        if g is None and cf is None and r is None and h is None and ac is None:
            return None
        g = 0.0 if g is None else self._clamp01(g)
        cf = g if cf is None else self._clamp01(cf)
        r = 0.0 if r is None else self._clamp01(r)
        h = 0.0 if h is None else self._clamp01(h)
        ac = 0.0 if ac is None else self._clamp01(ac)
        flag = self._regex_bool(text, r'"has_hallucination"\s*:\s*(true|false)')
        if flag is None:
            flag = h < self._HAS_HALLUCINATION_SCORE_FALLBACK_THRESHOLD
        reason = self._regex_reason(text)
        return g, cf, r, h, ac, flag, reason

    def _read_score(self, data: dict[str, Any], key: str, fallback_text: str) -> float | None:
        raw = data.get(key)
        if raw is not None:
            try:
                return float(raw)
            except (TypeError, ValueError):
                pass
        return self._regex_float(fallback_text, rf'"{re.escape(key)}"\s*:\s*{self._FLOAT_RE}')

    def _read_bool(self, data: dict[str, Any], text: str, hallucination_score: float) -> bool:
        raw = data.get("has_hallucination")
        if isinstance(raw, bool):
            return raw
        if isinstance(raw, str):
            return raw.strip().lower() in {"true", "1", "yes"}
        if raw is not None:
            try:
                return bool(raw)
            except (TypeError, ValueError):
                pass
        b = self._regex_bool(text, r'"has_hallucination"\s*:\s*(true|false)')
        if b is not None:
            return b
        return hallucination_score < self._HAS_HALLUCINATION_SCORE_FALLBACK_THRESHOLD

    def _read_reason(self, data: dict[str, Any]) -> str | None:
        raw = data.get("reason")
        if raw is None:
            return None
        if isinstance(raw, str):
            s = raw.strip()
            return s if s else None
        return str(raw)

    def _regex_float(self, text: str, pattern: str) -> float | None:
        match = re.search(pattern, text)
        if not match:
            return None
        try:
            return float(match.group(1))
        except (ValueError, IndexError):
            return None

    def _regex_bool(self, text: str, pattern: str) -> bool | None:
        match = re.search(pattern, text, flags=re.IGNORECASE)
        if not match:
            return None
        return match.group(1).lower() == "true"

    def _regex_reason(self, text: str) -> str | None:
        match = re.search(r'"reason"\s*:\s*"([^"]*)"', text)
        if not match:
            return None
        s = match.group(1).strip()
        return s if s else None

    @staticmethod
    def _clamp01(value: float) -> float:
        return max(0.0, min(1.0, float(value)))
