import uuid
import zipfile
from pathlib import Path

from unstructured.partition.docx import partition_docx
from unstructured.partition.pdf import partition_pdf
from unstructured.partition.pptx import partition_pptx

from src.core.config import INGESTION_CONFIG
from src.core.exceptions import OCRDependencyError
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
    page_start: int | None = None,
    page_end: int | None = None,
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
                "page_start": page_start,
                "page_end": page_end,
            },
        }
    )


def _partition_pdf_with_fallback(file_path: str):
    """
    Primary PDF extraction mode:
    - hi_res
    - infer_table_structure=True
    - extract_image_block_types=["Image"]
    - extract_image_block_to_payload=True

    If OCR-related extraction fails and fallback is enabled,
    degrade to the configured fallback strategy.
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

        if not INGESTION_CONFIG.enable_pdf_ocr_fallback:
            raise OCRDependencyError(
                f"OCR dependency error while extracting PDF '{file_path}': {exc}",
                user_message=(
                    "OCR dependency is missing for this PDF and OCR fallback is disabled. "
                    "Install `tesseract-ocr` in the runtime image and ensure it is available in PATH."
                ),
            ) from exc

    elements = partition_pdf(
        filename=file_path,
        strategy=INGESTION_CONFIG.pdf_strategy_fallback,
        infer_table_structure=True,
    )
    return elements, False


def _infer_image_title(elements, image_index: int) -> str | None:
    """
    Infer an image title/caption from nearby text on the same page.
    """
    current = elements[image_index]
    current_metadata = getattr(current, "metadata", None)
    current_page = getattr(current_metadata, "page_number", None)

    candidates: list[str] = []

    for offset in range(1, 4):
        idx = image_index - offset
        if idx < 0:
            break

        element = elements[idx]
        metadata = getattr(element, "metadata", None)
        page_number = getattr(metadata, "page_number", None)
        category = getattr(element, "category", None)
        text = (getattr(element, "text", None) or "").strip()

        if current_page is not None and page_number != current_page:
            continue

        if text and category != "Image":
            candidates.append(text[:200])
            break

    for offset in range(1, 3):
        idx = image_index + offset
        if idx >= len(elements):
            break

        element = elements[idx]
        metadata = getattr(element, "metadata", None)
        page_number = getattr(metadata, "page_number", None)
        category = getattr(element, "category", None)
        text = (getattr(element, "text", None) or "").strip()

        if current_page is not None and page_number != current_page:
            continue

        if text and category != "Image":
            candidates.append(text[:200])
            break

    if not candidates:
        return None

    title = candidates[0].strip()
    if len(title) > 160:
        title = title[:157] + "..."

    return title or None


def _infer_table_title(elements, table_index: int) -> str | None:
    current = elements[table_index]
    current_metadata = getattr(current, "metadata", None)
    current_page = getattr(current_metadata, "page_number", None)

    candidates: list[str] = []

    for offset in range(1, 4):
        idx = table_index - offset
        if idx < 0:
            break

        element = elements[idx]
        metadata = getattr(element, "metadata", None)
        page_number = getattr(metadata, "page_number", None)
        category = getattr(element, "category", None)
        text = (getattr(element, "text", None) or "").strip()

        if current_page is not None and page_number != current_page:
            continue

        if text and category != "Image":
            candidates.append(text[:200])
            break

    for offset in range(1, 3):
        idx = table_index + offset
        if idx >= len(elements):
            break

        element = elements[idx]
        metadata = getattr(element, "metadata", None)
        page_number = getattr(metadata, "page_number", None)
        category = getattr(element, "category", None)
        text = (getattr(element, "text", None) or "").strip()

        if current_page is not None and page_number != current_page:
            continue

        if text and category != "Image":
            candidates.append(text[:200])
            break

    if not candidates:
        return None

    title = candidates[0].strip()
    if len(title) > 160:
        title = title[:157] + "..."

    return title or None


def _extract_pdf_elements(
    file_path: str,
    source_file: str,
    max_text_chars_per_asset: int | None = None,
) -> list[dict]:
    """
    PDF extraction using Unstructured in raw hi_res mode.

    Primary extraction:
    - strategy="hi_res"
    - infer_table_structure=True
    - extract_image_block_types=["Image"]
    - extract_image_block_to_payload=True

    Fallback:
    - configured fallback strategy when OCR dependency is missing
    """
    if max_text_chars_per_asset is None:
        max_text_chars_per_asset = INGESTION_CONFIG.extraction_max_text_chars_per_asset

    elements, image_block_extraction_enabled = _partition_pdf_with_fallback(file_path)

    extracted: list[dict] = []
    text_buffer: list[str] = []
    text_buffer_start_index: int | None = None
    text_buffer_page_start: int | None = None
    text_buffer_page_end: int | None = None
    current_text_chars = 0

    for index, element in enumerate(elements):
        category = getattr(element, "category", None)
        text = (getattr(element, "text", None) or "").strip()
        metadata = getattr(element, "metadata", None)
        page_number = getattr(metadata, "page_number", None)

        if category in TEXTUAL_CATEGORIES_TO_SKIP:
            continue

        if category == "Table":
            _flush_text_buffer(
                extracted=extracted,
                text_buffer=text_buffer,
                source_file=source_file,
                start_index=text_buffer_start_index or index,
                end_index=index - 1,
                page_start=text_buffer_page_start,
                page_end=text_buffer_page_end,
            )
            text_buffer = []
            text_buffer_start_index = None
            text_buffer_page_start = None
            text_buffer_page_end = None
            current_text_chars = 0

            table_html = getattr(metadata, "text_as_html", None)
            raw_table_content = table_html or text

            if raw_table_content:
                table_title = _infer_table_title(elements, index)

                extracted.append(
                    {
                        "doc_id": str(uuid.uuid4()),
                        "content_type": "table",
                        "raw_content": raw_table_content,
                        "metadata": {
                            "source_file": source_file,
                            "element_index": index,
                            "element_category": category,
                            "page_number": getattr(metadata, "page_number", None),
                            "text_as_html": table_html,
                            "table_title": table_title,
                            "table_text": text,
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
                page_start=text_buffer_page_start,
                page_end=text_buffer_page_end,
            )
            text_buffer = []
            text_buffer_start_index = None
            text_buffer_page_start = None
            text_buffer_page_end = None
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
                            "image_title": _infer_image_title(elements, index),
                            "image_block_extraction_enabled": image_block_extraction_enabled,
                        },
                    }
                )
            continue

        if not text:
            continue

        if text_buffer_start_index is None:
            text_buffer_start_index = index
            text_buffer_page_start = page_number

        if page_number is not None:
            if text_buffer_page_start is None:
                text_buffer_page_start = page_number
            text_buffer_page_end = page_number

        if current_text_chars + len(text) > max_text_chars_per_asset and text_buffer:
            _flush_text_buffer(
                extracted=extracted,
                text_buffer=text_buffer,
                source_file=source_file,
                start_index=text_buffer_start_index,
                end_index=index - 1,
                page_start=text_buffer_page_start,
                page_end=text_buffer_page_end,
            )
            text_buffer = [text]
            text_buffer_start_index = index
            text_buffer_page_start = page_number
            text_buffer_page_end = page_number
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
        page_start=text_buffer_page_start,
        page_end=text_buffer_page_end,
    )

    return extracted


def _extract_docx_or_pptx_text_and_tables(
    file_path: str,
    source_file: str,
    max_text_chars_per_asset: int | None = None,
) -> list[dict]:
    if max_text_chars_per_asset is None:
        max_text_chars_per_asset = INGESTION_CONFIG.extraction_max_text_chars_per_asset

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
    text_buffer_page_start: int | None = None
    text_buffer_page_end: int | None = None
    current_text_chars = 0

    for index, element in enumerate(elements):
        category = getattr(element, "category", None)
        text = (getattr(element, "text", None) or "").strip()
        metadata = getattr(element, "metadata", None)
        page_number = getattr(metadata, "page_number", None)

        if category in TEXTUAL_CATEGORIES_TO_SKIP:
            continue

        if category == "Table":
            _flush_text_buffer(
                extracted=extracted,
                text_buffer=text_buffer,
                source_file=source_file,
                start_index=text_buffer_start_index or index,
                end_index=index - 1,
                page_start=text_buffer_page_start,
                page_end=text_buffer_page_end,
            )
            text_buffer = []
            text_buffer_start_index = None
            text_buffer_page_start = None
            text_buffer_page_end = None
            current_text_chars = 0

            table_html = getattr(metadata, "text_as_html", None)
            raw_table_content = table_html or text

            if raw_table_content:
                extracted.append(
                    {
                        "doc_id": str(uuid.uuid4()),
                        "content_type": "table",
                        "raw_content": raw_table_content,
                        "metadata": {
                            "source_file": source_file,
                            "element_index": index,
                            "element_category": category,
                            "page_number": getattr(metadata, "page_number", None),
                            "text_as_html": table_html,
                            "table_title": None,
                            "table_text": text,
                        },
                    }
                )
            continue

        if not text:
            continue

        if text_buffer_start_index is None:
            text_buffer_start_index = index
            text_buffer_page_start = page_number

        if page_number is not None:
            if text_buffer_page_start is None:
                text_buffer_page_start = page_number
            text_buffer_page_end = page_number

        if current_text_chars + len(text) > max_text_chars_per_asset and text_buffer:
            _flush_text_buffer(
                extracted=extracted,
                text_buffer=text_buffer,
                source_file=source_file,
                start_index=text_buffer_start_index,
                end_index=index - 1,
                page_start=text_buffer_page_start,
                page_end=text_buffer_page_end,
            )
            text_buffer = [text]
            text_buffer_start_index = index
            text_buffer_page_start = page_number
            text_buffer_page_end = page_number
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
        page_start=text_buffer_page_start,
        page_end=text_buffer_page_end,
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
                                "image_title": Path(media_name).stem,
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
    max_text_chars_per_asset: int | None = None,
) -> list[dict]:
    suffix = Path(file_path).suffix.lower()

    if max_text_chars_per_asset is None:
        max_text_chars_per_asset = INGESTION_CONFIG.extraction_max_text_chars_per_asset

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
