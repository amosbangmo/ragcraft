import os
from dataclasses import dataclass, field
from typing import Any

from dotenv import load_dotenv
from langchain_openai import ChatOpenAI, OpenAIEmbeddings

load_dotenv()


def _get_bool_env(name: str, default: bool) -> bool:
    value = os.getenv(name)
    if value is None:
        return default

    return value.strip().lower() in {"1", "true", "yes", "on"}


def _get_int_env(name: str, default: int) -> int:
    value = os.getenv(name)
    if value is None:
        return default

    try:
        return int(value)
    except ValueError:
        return default


def _get_float_env(name: str, default: float) -> float:
    value = os.getenv(name)
    if value is None or not value.strip():
        return default

    try:
        return float(value.strip())
    except ValueError:
        return default


def _get_str_env(name: str, default: str) -> str:
    value = os.getenv(name)
    if value is None or not value.strip():
        return default
    return value.strip()


@dataclass(frozen=True)
class RetrievalConfig:
    """
    Env-backed defaults for retrieval. Runtime / per-request tuning flows through
    ``RetrievalSettings`` and application-layer ``RetrievalSettingsTuner``
    (see ``domain.retrieval_settings``).
    """

    similarity_search_k: int = field(
        default_factory=lambda: _get_int_env("RAG_SIMILARITY_SEARCH_K", 25)
    )
    bm25_search_k: int = field(default_factory=lambda: _get_int_env("RAG_BM25_SEARCH_K", 25))
    hybrid_search_k: int = field(default_factory=lambda: _get_int_env("RAG_HYBRID_SEARCH_K", 25))
    bm25_k1: float = field(default_factory=lambda: _get_float_env("RAG_BM25_K1", 1.5))
    bm25_b: float = field(default_factory=lambda: _get_float_env("RAG_BM25_B", 0.75))
    bm25_epsilon: float = field(default_factory=lambda: _get_float_env("RAG_BM25_EPSILON", 0.25))
    rrf_k: int = field(default_factory=lambda: _get_int_env("RAG_RRF_K", 60))
    hybrid_beta: float = field(default_factory=lambda: _get_float_env("RAG_HYBRID_BETA", 0.5))
    max_prompt_assets: int = field(default_factory=lambda: _get_int_env("RAG_MAX_PROMPT_ASSETS", 5))
    max_text_chars_per_asset: int = field(
        default_factory=lambda: _get_int_env("RAG_MAX_TEXT_CHARS_PER_ASSET", 4000)
    )
    max_table_chars_per_asset: int = field(
        default_factory=lambda: _get_int_env("RAG_MAX_TABLE_CHARS_PER_ASSET", 4000)
    )
    enable_query_rewrite: bool = field(
        default_factory=lambda: _get_bool_env("RAG_ENABLE_QUERY_REWRITE", True)
    )
    query_rewrite_max_history_messages: int = field(
        default_factory=lambda: _get_int_env("RAG_QUERY_REWRITE_MAX_HISTORY_MESSAGES", 6)
    )
    enable_hybrid_retrieval: bool = field(
        default_factory=lambda: _get_bool_env("RAG_ENABLE_HYBRID_RETRIEVAL", True)
    )
    enable_contextual_compression: bool = field(
        default_factory=lambda: _get_bool_env("RAG_ENABLE_CONTEXTUAL_COMPRESSION", True)
    )
    enable_section_expansion: bool = field(
        default_factory=lambda: _get_bool_env("RAG_ENABLE_SECTION_EXPANSION", True)
    )
    section_expansion_neighbor_window: int = field(
        default_factory=lambda: _get_int_env("RAG_SECTION_EXPANSION_NEIGHBOR_WINDOW", 2)
    )
    section_expansion_max_per_section: int = field(
        default_factory=lambda: _get_int_env("RAG_SECTION_EXPANSION_MAX_PER_SECTION", 12)
    )
    section_expansion_global_max: int = field(
        default_factory=lambda: _get_int_env("RAG_SECTION_EXPANSION_GLOBAL_MAX", 64)
    )


@dataclass(frozen=True)
class IngestionConfig:
    """Ingestion limits; ``max_upload_bytes`` caps multipart upload bodies (chunked read in API adapter)."""

    max_upload_bytes: int = field(
        default_factory=lambda: _get_int_env("RAG_MAX_UPLOAD_BYTES", 100 * 1024 * 1024)
    )
    extraction_max_text_chars_per_asset: int = field(
        default_factory=lambda: _get_int_env("RAG_EXTRACTION_MAX_TEXT_CHARS_PER_ASSET", 2500)
    )
    summary_max_input_chars: int = field(
        default_factory=lambda: _get_int_env("RAG_SUMMARY_MAX_INPUT_CHARS", 4000)
    )
    pdf_strategy_default: str = field(
        default_factory=lambda: _get_str_env("RAG_PDF_STRATEGY_DEFAULT", "hi_res")
    )
    pdf_strategy_fallback: str = field(
        default_factory=lambda: _get_str_env("RAG_PDF_STRATEGY_FALLBACK", "fast")
    )
    enable_pdf_image_extraction: bool = field(
        default_factory=lambda: _get_bool_env("RAG_ENABLE_PDF_IMAGE_EXTRACTION", True)
    )
    enable_pdf_ocr_fallback: bool = field(
        default_factory=lambda: _get_bool_env("RAG_ENABLE_PDF_OCR_FALLBACK", True)
    )
    infer_table_structure: bool = field(
        default_factory=lambda: _get_bool_env("RAG_INFER_TABLE_STRUCTURE", True)
    )
    enable_text_chunking_by_title: bool = field(
        default_factory=lambda: _get_bool_env("RAG_ENABLE_TEXT_CHUNKING_BY_TITLE", True)
    )
    text_chunking_max_characters: int = field(
        default_factory=lambda: _get_int_env("RAG_TEXT_CHUNKING_MAX_CHARACTERS", 10000)
    )
    text_chunking_combine_text_under_n_chars: int = field(
        default_factory=lambda: _get_int_env("RAG_TEXT_CHUNKING_COMBINE_UNDER", 2000)
    )
    text_chunking_new_after_n_chars: int = field(
        default_factory=lambda: _get_int_env("RAG_TEXT_CHUNKING_NEW_AFTER", 6000)
    )
    text_chunking_multipage_sections: bool = field(
        default_factory=lambda: _get_bool_env("RAG_TEXT_CHUNKING_MULTIPAGE_SECTIONS", False)
    )


@dataclass(frozen=True)
class UserProfileUploadConfig:
    """
    Caps for profile multipart bodies (e.g. avatars).

    The HTTP layer reads uploads in chunks and stops at ``max_avatar_bytes``; see
    ``interfaces.http.upload_adapter``.
    """

    max_avatar_bytes: int = field(
        default_factory=lambda: _get_int_env("RAG_MAX_AVATAR_UPLOAD_BYTES", 2 * 1024 * 1024)
    )


@dataclass(frozen=True)
class RAGConfig:
    retrieval: RetrievalConfig = field(default_factory=RetrievalConfig)
    ingestion: IngestionConfig = field(default_factory=IngestionConfig)
    user_profile_upload: UserProfileUploadConfig = field(default_factory=UserProfileUploadConfig)


OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

if not OPENAI_API_KEY:
    raise ValueError("OPENAI_API_KEY is missing")

# HTTP E2E / local artifact runs use this placeholder so no real OpenAI traffic is required.
CI_PLACEHOLDER_OPENAI_API_KEY = "ci-test-key"


def _openai_request_timeout() -> float | None:
    """Optional OpenAI HTTP timeout (seconds). Unset or non-positive → langchain default."""
    raw = os.getenv("OPENAI_REQUEST_TIMEOUT_S")
    if raw is None or not raw.strip():
        return None
    try:
        value = float(raw.strip())
    except ValueError:
        return None
    return value if value > 0 else None


_OPENAI_REQUEST_TIMEOUT = _openai_request_timeout()

APP_CONFIG = RAGConfig()
RETRIEVAL_CONFIG = APP_CONFIG.retrieval
INGESTION_CONFIG = APP_CONFIG.ingestion
USER_PROFILE_UPLOAD_CONFIG = APP_CONFIG.user_profile_upload

_USE_CI_HTTP_LLM_STUBS = OPENAI_API_KEY.strip() == CI_PLACEHOLDER_OPENAI_API_KEY
# Match ``text-embedding-3-small`` width so FAISS indices built under the stub stay consistent.
_FAKE_EMBEDDING_DIM = _get_int_env("RAGCRAFT_CI_FAKE_EMBEDDING_DIM", 1536)


class _CiPlaceholderChatModel:
    """
    In-process LLM stand-in when ``OPENAI_API_KEY`` is the CI/E2E placeholder.

    Avoids hung HTTP calls (LangChain → OpenAI) that caused Cypress and artifact runs to hit
    multi-minute timeouts. Routes a minimal JSON line for the LLM-judge prompt shape.
    """

    _JUDGE_HEAD = "You are an expert evaluator for retrieval-augmented"
    _REWRITE_HEAD = "You rewrite user questions into compact retrieval queries"

    def invoke(self, input: Any, config: Any = None, **kwargs: Any) -> Any:
        del config, kwargs
        from langchain_core.messages import AIMessage

        prompt = input if isinstance(input, str) else str(input)
        if self._JUDGE_HEAD in prompt:
            content = (
                '{"groundedness_score":0.9,"citation_faithfulness_score":0.9,'
                '"answer_relevance_score":0.9,"hallucination_score":0.85,'
                '"answer_correctness_score":0.88,"has_hallucination":false,'
                '"reason":"ci-test-key stub judge"}'
            )
        elif self._REWRITE_HEAD in prompt:
            marker = "Original question:\n"
            idx = prompt.rfind(marker)
            if idx != -1:
                tail = prompt[idx + len(marker) :].strip()
                line = tail.split("\n", 1)[0].strip()
                content = line if line else "e2e retrieval query"
            else:
                content = "e2e retrieval query"
        else:
            content = (
                "E2E stub answer (ci-test-key): placeholder response for HTTP tests; "
                "no external LLM call."
            )
        return AIMessage(content=content)


if _USE_CI_HTTP_LLM_STUBS:
    from langchain_core.embeddings import DeterministicFakeEmbedding

    EMBEDDINGS = DeterministicFakeEmbedding(size=_FAKE_EMBEDDING_DIM)
    LLM = _CiPlaceholderChatModel()
else:
    _embeddings_kwargs: dict = {
        "api_key": OPENAI_API_KEY,
        "model": _get_str_env("OPENAI_EMBEDDINGS_MODEL", "text-embedding-3-small"),
    }
    _llm_kwargs: dict = {
        "api_key": OPENAI_API_KEY,
        "model": _get_str_env("OPENAI_CHAT_MODEL", "gpt-4o-mini"),
        "temperature": float(os.getenv("OPENAI_CHAT_TEMPERATURE", "0")),
    }
    if _OPENAI_REQUEST_TIMEOUT is not None:
        _embeddings_kwargs["request_timeout"] = _OPENAI_REQUEST_TIMEOUT
        _llm_kwargs["request_timeout"] = _OPENAI_REQUEST_TIMEOUT

    EMBEDDINGS = OpenAIEmbeddings(**_embeddings_kwargs)
    LLM = ChatOpenAI(**_llm_kwargs)
# NOTE: module-level ``LLM`` / ``EMBEDDINGS`` singletons; moving construction behind the composition root is a separate refactor (see ARCHITECTURE_TARGET.md).
