from infrastructure.config.config import LLM


class QueryRewriteService:
    """
    Rewrite user questions into retrieval-optimized search queries.

    Design goals:
    - preserve meaning
    - preserve named entities, dates, numbers, acronyms
    - optionally use a short chat history window
    - never block the pipeline if rewriting fails
    """

    def __init__(self, max_history_messages: int = 6):
        self.max_history_messages = max_history_messages

    def rewrite(
        self,
        *,
        question: str,
        chat_history: list[str] | None = None,
        max_history_messages: int | None = None,
    ) -> str:
        normalized_question = (question or "").strip()
        if not normalized_question:
            return normalized_question

        history = chat_history or []
        limit = (
            self.max_history_messages
            if max_history_messages is None
            else max(0, int(max_history_messages))
        )
        history_tail = history[-limit:]
        history_text = "\n".join(history_tail) if history_tail else "No prior chat history."

        prompt = f"""
You rewrite user questions into compact retrieval queries for a RAG system.

Goal:
- maximize search recall and precision
- keep the original meaning
- preserve technical terms, entities, file/domain vocabulary, dates, numbers, abbreviations
- resolve obvious conversational references using the chat history if helpful

Rules:
- return only the rewritten retrieval query
- do not answer the question
- do not add explanations
- keep it concise but information-dense
- if the original question is already good for retrieval, return it almost unchanged

Chat history:
{history_text}

Original question:
{normalized_question}
""".strip()

        try:
            response = LLM.invoke(prompt)
            rewritten = getattr(response, "content", str(response)).strip()
        except Exception:
            return normalized_question

        if not rewritten:
            return normalized_question

        return rewritten
