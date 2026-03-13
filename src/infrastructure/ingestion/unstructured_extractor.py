import uuid
import zipfile
from pathlib import Path

from unstructured.partition.docx import partition_docx
from unstructured.partition.pdf import partition_pdf
from unstructured.partition.pptx import partition_pptx

from src.infrastructure.ingestion.image_utils import (
    bytes_to_base64,
    guess_mime_type_from_suffix,
)


TEXTUAL_CATEGORIES_TO_SKIP = {"Header", "Footer", "PageBreak"}
DOCX_MEDIA_PREFIX = "word/media/"
PPTX_MEDIA_PREFIX = "ppt/media/"


def _is_tesseract_missing_error(exc: Exception) -> bool:
    message = str(exc).lower()
    return "tesseract is not installed" in message or "tesseractnotfounderror" in message


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


def _partition_pdf_with_fallback(file_path: str):
    """
    First try hi_res to get true Image blocks from Unstructured.
    If Tesseract is unavailable, degrade to fast mode so ingestion can continue.
    """
    try:
        elements = partition_pdf(
            filename=file_path,
            strategy="hi_res",
            infer_table_structure=True,
            extract_image_block_types=["Image"],
            extract_image_block_to_payload=True,
        )
        return elements, True
    except Exception as exc:
        if not _is_tesseract_missing_error(exc):
            raise

    elements = partition_pdf(
        filename=file_path,
        strategy="fast",
        infer_table_structure=True,
    )
    return elements, False


def _extract_pdf_elements(
    file_path: str,
    source_file: str,
    max_text_chars_per_asset: int = 2500,
) -> list[dict]:
    """
    PDF path using Unstructured layout extraction.

    Returns:
    - text assets
    - table assets
    - image assets only when hi_res succeeds
    """
    elements, image_block_extraction_enabled = _partition_pdf_with_fallback(file_path)

    extracted: list[dict] = []
    text_buffer: list[str] = []
    text_buffer_start_index: int | None = None
    current_text_chars = 0

    for index, element in enumerate(elements):
        category = getattr(element, "category", None)
        text = (getattr(element, "text", None) or "").strip()
        metadata = getattr(element, "metadata", None)

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
                            "page_number": getattr(metadata, "page_number", None),
                            "text_as_html": getattr(metadata, "text_as_html", None),
                            "image_block_extraction_enabled": image_block_extraction_enabled,
                        },
                    }
                )
            continue

        if category == "Image":
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

            image_base64 = getattr(metadata, "image_base64", None)
            image_mime_type = getattr(metadata, "image_mime_type", None)

            if image_base64:
                extracted.append(
                    {
                        "doc_id": str(uuid.uuid4()),
                        "content_type": "image",
                        "raw_content": image_base64,
                        "metadata": {
                            "source_file": source_file,
                            "element_index": index,
                            "element_category": category,
                            "page_number": getattr(metadata, "page_number", None),
                            "image_mime_type": image_mime_type,
                            "image_block_extraction_enabled": image_block_extraction_enabled,
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

    return extracted


def _extract_docx_or_pptx_text_and_tables(
    file_path: str,
    source_file: str,
    max_text_chars_per_asset: int = 2500,
) -> list[dict]:
    suffix = Path(file_path).suffix.lower()

    if suffix == ".docx":
        elements = partition_docx(filename=file_path)
    elif suffix == ".pptx":
        elements = partition_pptx(filename=file_path)
    else:
        raise ValueError(f"Unsupported file type: {suffix}")

    extracted: list[dict] = []
    text_buffer: list[str] = []
    text_buffer_start_index: int | None = None
    current_text_chars = 0

    for index, element in enumerate(elements):
        category = getattr(element, "category", None)
        text = (getattr(element, "text", None) or "").strip()
        metadata = getattr(element, "metadata", None)

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
                            "page_number": getattr(metadata, "page_number", None),
                            "text_as_html": getattr(metadata, "text_as_html", None),
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

    return extracted


def _extract_embedded_images_from_zip(
    file_path: str,
    source_file: str,
    media_prefix: str,
    category_name: str,
) -> list[dict]:
    extracted: list[dict] = []

    try:
        with zipfile.ZipFile(file_path, "r") as archive:
            media_files = [
                name for name in archive.namelist()
                if name.startswith(media_prefix) and not name.endswith("/")
            ]

            for image_index, media_name in enumerate(media_files, start=1):
                try:
                    image_bytes = archive.read(media_name)
                    image_base64 = bytes_to_base64(image_bytes)

                    extracted.append(
                        {
                            "doc_id": str(uuid.uuid4()),
                            "content_type": "image",
                            "raw_content": image_base64,
                            "metadata": {
                                "source_file": source_file,
                                "element_category": category_name,
                                "embedded_path": media_name,
                                "image_index": image_index,
                                "image_mime_type": guess_mime_type_from_suffix(media_name),
                            },
                        }
                    )
                except Exception:
                    continue
    except Exception:
        return []

    return extracted


def extract_elements(
    file_path: str,
    source_file: str,
    max_text_chars_per_asset: int = 2500,
) -> list[dict]:
    suffix = Path(file_path).suffix.lower()

    if suffix == ".pdf":
        return _extract_pdf_elements(
            file_path=file_path,
            source_file=source_file,
            max_text_chars_per_asset=max_text_chars_per_asset,
        )

    if suffix == ".docx":
        extracted = _extract_docx_or_pptx_text_and_tables(
            file_path=file_path,
            source_file=source_file,
            max_text_chars_per_asset=max_text_chars_per_asset,
        )
        extracted.extend(
            _extract_embedded_images_from_zip(
                file_path=file_path,
                source_file=source_file,
                media_prefix=DOCX_MEDIA_PREFIX,
                category_name="docx_embedded_image_fallback",
            )
        )
        return extracted

    if suffix == ".pptx":
        extracted = _extract_docx_or_pptx_text_and_tables(
            file_path=file_path,
            source_file=source_file,
            max_text_chars_per_asset=max_text_chars_per_asset,
        )
        extracted.extend(
            _extract_embedded_images_from_zip(
                file_path=file_path,
                source_file=source_file,
                media_prefix=PPTX_MEDIA_PREFIX,
                category_name="pptx_embedded_image_fallback",
            )
        )
        return extracted

    raise ValueError(f"Unsupported file type: {suffix}")
