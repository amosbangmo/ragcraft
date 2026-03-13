import base64
import uuid
from pathlib import Path

from unstructured.partition.docx import partition_docx
from unstructured.partition.pdf import partition_pdf
from unstructured.partition.pptx import partition_pptx


SUPPORTED_BINARY_FALLBACK_SUFFIXES = {".pdf", ".docx", ".pptx"}
TEXTUAL_CATEGORIES_TO_SKIP = {"Header", "Footer", "PageBreak"}


def _read_file_as_base64(file_path: str) -> str:
    with open(file_path, "rb") as f:
        return base64.b64encode(f.read()).decode("utf-8")


def _partition_file(file_path: str):
    suffix = Path(file_path).suffix.lower()

    if suffix == ".pdf":
        # Much more stable than partition.auto for a first production-grade increment
        return partition_pdf(
            filename=file_path,
            strategy="fast",
        )

    if suffix == ".docx":
        return partition_docx(filename=file_path)

    if suffix == ".pptx":
        return partition_pptx(filename=file_path)

    raise ValueError(f"Unsupported file type: {suffix}")


def _flush_text_buffer(
    extracted: list[dict],
    text_buffer: list[str],
    source_file: str,
    start_index: int,
    end_index: int,
):
    if not text_buffer:
        return

    raw_text = "\n\n".join(part for part in text_buffer if part.strip()).strip()

    if not raw_text:
        return

    extracted.append(
        {
            "doc_id": str(uuid.uuid4()),
            "content_type": "text",
            "raw_content": raw_text,
            "metadata": {
                "source_file": source_file,
                "element_category": "merged_text",
                "start_element_index": start_index,
                "end_element_index": end_index,
            },
        }
    )


def extract_elements(
    file_path: str,
    source_file: str,
    max_text_chars_per_asset: int = 2500,
) -> list[dict]:
    """
    Stable extraction pass for PR1:
    - table elements are kept as individual assets
    - text elements are merged into larger chunks to avoid hundreds of LLM calls
    - one binary image fallback asset is stored for later multimodal evolution
    """
    elements = _partition_file(file_path)
    extracted: list[dict] = []

    text_buffer: list[str] = []
    text_buffer_start_index: int | None = None
    current_text_chars = 0

    for index, element in enumerate(elements):
        category = getattr(element, "category", None)
        text = (getattr(element, "text", None) or "").strip()

        if category in TEXTUAL_CATEGORIES_TO_SKIP:
            continue

        if category == "Table":
            _flush_text_buffer(
                extracted=extracted,
                text_buffer=text_buffer,
                source_file=source_file,
                start_index=text_buffer_start_index or index,
                end_index=index - 1,
            )
            text_buffer = []
            text_buffer_start_index = None
            current_text_chars = 0

            if text:
                extracted.append(
                    {
                        "doc_id": str(uuid.uuid4()),
                        "content_type": "table",
                        "raw_content": text,
                        "metadata": {
                            "source_file": source_file,
                            "element_index": index,
                            "element_category": category,
                        },
                    }
                )
            continue

        if not text:
            continue

        if text_buffer_start_index is None:
            text_buffer_start_index = index

        if current_text_chars + len(text) > max_text_chars_per_asset and text_buffer:
            _flush_text_buffer(
                extracted=extracted,
                text_buffer=text_buffer,
                source_file=source_file,
                start_index=text_buffer_start_index,
                end_index=index - 1,
            )
            text_buffer = [text]
            text_buffer_start_index = index
            current_text_chars = len(text)
        else:
            text_buffer.append(text)
            current_text_chars += len(text)

    _flush_text_buffer(
        extracted=extracted,
        text_buffer=text_buffer,
        source_file=source_file,
        start_index=text_buffer_start_index or 0,
        end_index=len(elements) - 1,
    )

    suffix = Path(file_path).suffix.lower()
    if suffix in SUPPORTED_BINARY_FALLBACK_SUFFIXES:
        extracted.append(
            {
                "doc_id": str(uuid.uuid4()),
                "content_type": "image",
                "raw_content": _read_file_as_base64(file_path),
                "metadata": {
                    "source_file": source_file,
                    "element_category": "document_binary_fallback",
                    "mime_hint": suffix.replace(".", ""),
                    "note": (
                        "Temporary fallback visual asset representation. "
                        "Not summarized by the LLM in PR1."
                    ),
                },
            }
        )

    return extracted
