import uuid
import zipfile
from pathlib import Path

from unstructured.chunking.title import chunk_by_title
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

MAX_ORIG_ELEMENT_PREVIEWS = 12
MAX_ORIG_ELEMENT_TEXT_PREVIEW_CHARS = 240


def _is_tesseract_missing_error(exc: Exception) -> bool:
    message = str(exc).lower()
    return "tesseract is not installed" in message or "tesseractnotfounderror" in message


def _set_runtime_element_metadata(element, source_file: str, element_index: int) -> None:
    """
    Attach runtime-only metadata used to reconstruct chunk traceability
    after chunk_by_title() grouping.
    """
    metadata = getattr(element, "metadata", None)

    try:
        setattr(element, "_rag_element_index", element_index)
    except Exception:
        pass

    try:
        setattr(element, "_rag_source_file", source_file)
    except Exception:
        pass

    if metadata is None:
        return

    try:
        setattr(metadata, "rag_element_index", element_index)
    except Exception:
        pass

    try:
        setattr(metadata, "rag_source_file", source_file)
    except Exception:
        pass


def _get_runtime_element_index(element) -> int | None:
    index = getattr(element, "_rag_element_index", None)
    if index is not None:
        return index

    metadata = getattr(element, "metadata", None)
    return getattr(metadata, "rag_element_index", None)


def _get_page_number(element) -> int | None:
    metadata = getattr(element, "metadata", None)
    return getattr(metadata, "page_number", None)


def _is_textual_element(element) -> bool:
    category = getattr(element, "category", None)
    text = (getattr(element, "text", None) or "").strip()

    if category in TEXTUAL_CATEGORIES_TO_SKIP:
        return False

    if category in {"Table", "Image"}:
        return False

    return bool(text)


def _build_orig_element_preview(element) -> dict | None:
    text = (getattr(element, "text", None) or "").strip()
    category = getattr(element, "category", None)
    page_number = _get_page_number(element)
    element_index = _get_runtime_element_index(element)

    if not text and not category:
        return None

    if len(text) > MAX_ORIG_ELEMENT_TEXT_PREVIEW_CHARS:
        text_preview = text[: MAX_ORIG_ELEMENT_TEXT_PREVIEW_CHARS - 3] + "..."
    else:
        text_preview = text

    return {
        "element_index": element_index,
        "page_number": page_number,
        "category": category,
        "text_preview": text_preview,
    }


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


def _build_text_asset_from_chunk(chunk, source_file: str) -> dict | None:
    raw_text = (getattr(chunk, "text", None) or "").strip()
    if not raw_text:
        return None

    chunk_metadata = getattr(chunk, "metadata", None)
    orig_elements = getattr(chunk_metadata, "orig_elements", None) or []

    element_indices: list[int] = []
    page_numbers: list[int] = []
    orig_categories: list[str] = []
    orig_previews: list[dict] = []
    orig_total_text_chars = 0
    title_candidates: list[str] = []

    for orig_element in orig_elements:
        element_index = _get_runtime_element_index(orig_element)
        if element_index is not None:
            element_indices.append(element_index)

        page_number = _get_page_number(orig_element)
        if page_number is not None:
            page_numbers.append(page_number)

        category = getattr(orig_element, "category", None)
        if category:
            orig_categories.append(category)

        orig_text = (getattr(orig_element, "text", None) or "").strip()
        orig_total_text_chars += len(orig_text)

        if category == "Title" and orig_text:
            title_candidates.append(orig_text[:160])

        preview = _build_orig_element_preview(orig_element)
        if preview is not None and len(orig_previews) < MAX_ORIG_ELEMENT_PREVIEWS:
            orig_previews.append(preview)

    start_index = min(element_indices) if element_indices else None
    end_index = max(element_indices) if element_indices else None
    page_start = min(page_numbers) if page_numbers else None
    page_end = max(page_numbers) if page_numbers else None

    return {
        "doc_id": str(uuid.uuid4()),
        "content_type": "text",
        "raw_content": raw_text,
        "metadata": {
            "source_file": source_file,
            "element_category": getattr(chunk, "category", "CompositeElement"),
            "start_element_index": start_index,
            "end_element_index": end_index,
            "page_start": page_start,
            "page_end": page_end,
            "chunking_strategy": "by_title",
            "orig_element_count": len(orig_elements),
            "orig_element_categories": sorted(set(orig_categories)),
            "orig_elements_preview": orig_previews,
            "orig_elements_preview_truncated": len(orig_elements) > len(orig_previews),
            "orig_total_text_chars": orig_total_text_chars,
            "chunk_char_count": len(raw_text),
            "chunk_title": title_candidates[0] if title_candidates else None,
        },
    }


def _flush_text_run(
    extracted: list[dict],
    text_run: list,
    source_file: str,
) -> None:
    if not text_run:
        return

    if not INGESTION_CONFIG.enable_text_chunking_by_title:
        raw_text = "\n\n".join(
            (getattr(element, "text", None) or "").strip()
            for element in text_run
            if (getattr(element, "text", None) or "").strip()
        ).strip()

        if not raw_text:
            return

        element_indices = [idx for idx in (_get_runtime_element_index(e) for e in text_run) if idx is not None]
        page_numbers = [pn for pn in (_get_page_number(e) for e in text_run) if pn is not None]
        orig_previews = [
            preview
            for preview in (_build_orig_element_preview(element) for element in text_run)
            if preview is not None
        ]

        extracted.append(
            {
                "doc_id": str(uuid.uuid4()),
                "content_type": "text",
                "raw_content": raw_text,
                "metadata": {
                    "source_file": source_file,
                    "element_category": "merged_text",
                    "start_element_index": min(element_indices) if element_indices else None,
                    "end_element_index": max(element_indices) if element_indices else None,
                    "page_start": min(page_numbers) if page_numbers else None,
                    "page_end": max(page_numbers) if page_numbers else None,
                    "chunking_strategy": "none",
                    "orig_element_count": len(text_run),
                    "orig_element_categories": sorted(
                        {
                            getattr(element, "category", None)
                            for element in text_run
                            if getattr(element, "category", None)
                        }
                    ),
                    "orig_elements_preview": orig_previews[:MAX_ORIG_ELEMENT_PREVIEWS],
                    "orig_elements_preview_truncated": len(orig_previews) > MAX_ORIG_ELEMENT_PREVIEWS,
                    "orig_total_text_chars": len(raw_text),
                    "chunk_char_count": len(raw_text),
                    "chunk_title": None,
                },
            }
        )
        return

    chunks = chunk_by_title(
        text_run,
        max_characters=INGESTION_CONFIG.text_chunking_max_characters,
        combine_text_under_n_chars=INGESTION_CONFIG.text_chunking_combine_text_under_n_chars,
        new_after_n_chars=INGESTION_CONFIG.text_chunking_new_after_n_chars,
        multipage_sections=INGESTION_CONFIG.text_chunking_multipage_sections,
    )

    for chunk in chunks:
        asset = _build_text_asset_from_chunk(chunk, source_file)
        if asset:
            extracted.append(asset)


def _append_table_asset(
    extracted: list[dict],
    elements: list,
    element_index: int,
    element,
    source_file: str,
    image_block_extraction_enabled: bool,
) -> None:
    metadata = getattr(element, "metadata", None)
    text = (getattr(element, "text", None) or "").strip()

    table_html = getattr(metadata, "text_as_html", None)
    raw_table_content = table_html or text

    if not raw_table_content:
        return

    extracted.append(
        {
            "doc_id": str(uuid.uuid4()),
            "content_type": "table",
            "raw_content": raw_table_content,
            "metadata": {
                "source_file": source_file,
                "element_index": element_index,
                "element_category": "Table",
                "page_number": getattr(metadata, "page_number", None),
                "text_as_html": table_html,
                "table_title": _infer_table_title(elements, element_index),
                "table_text": text,
                "image_block_extraction_enabled": image_block_extraction_enabled,
            },
        }
    )


def _append_image_asset(
    extracted: list[dict],
    elements: list,
    element_index: int,
    element,
    source_file: str,
    image_block_extraction_enabled: bool,
) -> None:
    metadata = getattr(element, "metadata", None)
    image_base64 = getattr(metadata, "image_base64", None)

    if not image_base64:
        return

    extracted.append(
        {
            "doc_id": str(uuid.uuid4()),
            "content_type": "image",
            "raw_content": image_base64,
            "metadata": {
                "source_file": source_file,
                "element_index": element_index,
                "element_category": "Image",
                "page_number": getattr(metadata, "page_number", None),
                "image_mime_type": getattr(metadata, "image_mime_type", None),
                "image_title": _infer_image_title(elements, element_index),
                "image_block_extraction_enabled": image_block_extraction_enabled,
            },
        }
    )


def _extract_partitioned_elements(
    elements: list,
    source_file: str,
    *,
    image_block_extraction_enabled: bool,
) -> list[dict]:
    """
    Build multimodal assets while only chunking textual runs.
    Tables and images remain isolated and unchanged.
    """
    extracted: list[dict] = []
    text_run: list = []

    for index, element in enumerate(elements):
        _set_runtime_element_metadata(element, source_file, index)

        category = getattr(element, "category", None)

        if category in TEXTUAL_CATEGORIES_TO_SKIP:
            continue

        if _is_textual_element(element):
            text_run.append(element)
            continue

        _flush_text_run(extracted, text_run, source_file)
        text_run = []

        if category == "Table":
            _append_table_asset(
                extracted=extracted,
                elements=elements,
                element_index=index,
                element=element,
                source_file=source_file,
                image_block_extraction_enabled=image_block_extraction_enabled,
            )
            continue

        if category == "Image":
            _append_image_asset(
                extracted=extracted,
                elements=elements,
                element_index=index,
                element=element,
                source_file=source_file,
                image_block_extraction_enabled=image_block_extraction_enabled,
            )
            continue

    _flush_text_run(extracted, text_run, source_file)

    return extracted


def _extract_pdf_elements(
    file_path: str,
    source_file: str,
    max_text_chars_per_asset: int | None = None,
) -> list[dict]:
    """
    PDF extraction using Unstructured in raw hi_res mode, then text-only chunking.

    Primary extraction:
    - strategy="hi_res"
    - infer_table_structure=True
    - extract_image_block_types=["Image"]
    - extract_image_block_to_payload=True

    Then:
    - only textual runs are chunked with chunk_by_title(...)
    - tables and images are preserved as separate assets
    """
    elements, image_block_extraction_enabled = _partition_pdf_with_fallback(file_path)

    return _extract_partitioned_elements(
        elements=elements,
        source_file=source_file,
        image_block_extraction_enabled=image_block_extraction_enabled,
    )


def _extract_docx_or_pptx_text_and_tables(
    file_path: str,
    source_file: str,
    max_text_chars_per_asset: int | None = None,
) -> list[dict]:
    suffix = Path(file_path).suffix.lower()

    if suffix == ".docx":
        elements = partition_docx(filename=file_path)
    elif suffix == ".pptx":
        elements = partition_pptx(filename=file_path)
    else:
        raise ValueError(f"Unsupported file type: {suffix}")

    return _extract_partitioned_elements(
        elements=elements,
        source_file=source_file,
        image_block_extraction_enabled=False,
    )


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
