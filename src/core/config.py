import os
from dataclasses import dataclass, field

from dotenv import load_dotenv
from langchain_openai import OpenAIEmbeddings, ChatOpenAI


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


def _get_str_env(name: str, default: str) -> str:
    value = os.getenv(name)
    if value is None or not value.strip():
        return default
    return value.strip()


@dataclass(frozen=True)
class RetrievalConfig:
    retrieval_k: int = field(default_factory=lambda: _get_int_env("RAG_RETRIEVAL_K", 15))
    max_prompt_assets: int = field(default_factory=lambda: _get_int_env("RAG_MAX_PROMPT_ASSETS", 5))
    max_text_chars_per_asset: int = field(default_factory=lambda: _get_int_env("RAG_MAX_TEXT_CHARS_PER_ASSET", 4000))
    max_table_chars_per_asset: int = field(default_factory=lambda: _get_int_env("RAG_MAX_TABLE_CHARS_PER_ASSET", 4000))


@dataclass(frozen=True)
class IngestionConfig:
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
class RAGConfig:
    retrieval: RetrievalConfig = field(default_factory=RetrievalConfig)
    ingestion: IngestionConfig = field(default_factory=IngestionConfig)


OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

if not OPENAI_API_KEY:
    raise ValueError("OPENAI_API_KEY is missing")


APP_CONFIG = RAGConfig()
RETRIEVAL_CONFIG = APP_CONFIG.retrieval
INGESTION_CONFIG = APP_CONFIG.ingestion


EMBEDDINGS = OpenAIEmbeddings(
    api_key=OPENAI_API_KEY,
    model=_get_str_env("OPENAI_EMBEDDINGS_MODEL", "text-embedding-3-small"),
)

LLM = ChatOpenAI(
    api_key=OPENAI_API_KEY,
    model=_get_str_env("OPENAI_CHAT_MODEL", "gpt-4o-mini"),
    temperature=float(os.getenv("OPENAI_CHAT_TEMPERATURE", "0")),
)
