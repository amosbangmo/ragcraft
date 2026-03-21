import re
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


# ---------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------

TEXTUAL_CATEGORIES_TO_SKIP = {"Header", "Footer", "PageBreak"}

DOCX_MEDIA_PREFIX = "word/media/"
PPTX_MEDIA_PREFIX = "ppt/media/"

# Regex used to detect captions like:
# "Figure 3", "Fig. 4", "Table 1", "Tableau 2"
_CAPTION_RE = re.compile(
    r"^\s*(figure|fig\.?|table|tableau)\s*[A-Za-z0-9\-.:]*",
    re.IGNORECASE,
)


# ---------------------------------------------------------------------
# Small helpers
# ---------------------------------------------------------------------

def _metadata_of(element):
    """Safely access the metadata attribute of an Unstructured element."""
    return getattr(element, "metadata", None)


def _text_of(element) -> str:
    """Return trimmed text content from an element."""
    return (getattr(element, "text", None) or "").strip()


def _category_of(element):
    """Return the element category."""
    return getattr(element, "category", None)


def _page_number_of(element) -> int | None:
    """Return the page number if available."""
    metadata = _metadata_of(element)
    return getattr(metadata, "page_number", None)


# ---------------------------------------------------------------------
# OCR fallback detection
# ---------------------------------------------------------------------

def _is_tesseract_missing_error(exc: Exception) -> bool:
    """
    Detect if the exception is caused by a missing Tesseract installation.
    """
    message = str(exc).lower()
    return "tesseract is not installed" in message or "tesseractnotfounderror" in message


# ---------------------------------------------------------------------
# Runtime metadata for traceability
# ---------------------------------------------------------------------

def _set_runtime_element_metadata(element, element_index: int) -> None:
    """
    Attach runtime metadata to each element.

    This is required because `chunk_by_title` groups elements together,
    and we later want to reconstruct which original elements formed a chunk.
    """
    metadata = _metadata_of(element)

    try:
        setattr(element, "_rag_element_index", element_index)
    except Exception:
        pass

    if metadata is not None:
        try:
            setattr(metadata, "rag_element_index", element_index)
        except Exception:
            pass


def _get_runtime_element_index(element) -> int | None:
    """
    Retrieve the stored runtime element index.
    """
    index = getattr(element, "_rag_element_index", None)
    if index is not None:
        return index

    metadata = _metadata_of(element)
    return getattr(metadata, "rag_element_index", None)


# ---------------------------------------------------------------------
# Element classification
# ---------------------------------------------------------------------

def _is_textual_element(element) -> bool:
    """
    Determine whether an element should be treated as textual content.
    """
    category = _category_of(element)
    text = _text_of(element)

    if category in TEXTUAL_CATEGORIES_TO_SKIP:
        return False

    if category in {"Table", "Image"}:
        return False

    return bool(text)


# ---------------------------------------------------------------------
# Caption inference
# ---------------------------------------------------------------------

def _infer_nearby_title(elements: list, element_index: int) -> str | None:
    """
    Try to infer a caption for an image or table by inspecting nearby text.

    Strategy:
    1. Prefer explicit captions ("Figure", "Fig.", "Table", etc.) on the same page
    2. Otherwise use the closest nearby text on the same page
    3. Finally fallback to explicit captions on adjacent pages
    """

    current_page = _page_number_of(elements[element_index])

    def candidate(idx: int, allow_adjacent_page: bool = False) -> str | None:
        if idx < 0 or idx >= len(elements):
            return None

        element = elements[idx]
        page = _page_number_of(element)

        same_page = page == current_page
        adjacent_page = (
            current_page is not None
            and page in {current_page - 1, current_page + 1}
        )

        if not same_page and not (allow_adjacent_page and adjacent_page):
            return None

        if _category_of(element) == "Image":
            return None

        text = _text_of(element)
        if not text:
            return None

        if len(text) > 160:
            return text[:157] + "..."

        return text

    nearby_same_page = [
        element_index - 1,
        element_index - 2,
        element_index - 3,
        element_index + 1,
        element_index + 2,
    ]

    nearby_adjacent_pages = [
        element_index - 1,
        element_index - 2,
        element_index + 1,
        element_index + 2,
    ]

    # Prefer explicit captions
    for idx in nearby_same_page:
        text = candidate(idx)
        if text and _CAPTION_RE.match(text):
            return text

    # Otherwise return closest nearby text
    for idx in nearby_same_page:
        text = candidate(idx)
        if text:
            return text

    # Fallback: explicit captions on adjacent pages
    for idx in nearby_adjacent_pages:
        text = candidate(idx, allow_adjacent_page=True)
        if text and _CAPTION_RE.match(text):
            return text

    return None


# ---------------------------------------------------------------------
# PDF partition with OCR fallback
# ---------------------------------------------------------------------

def _partition_pdf_with_fallback(file_path: str):
    """
    Extract PDF elements using the preferred strategy.

    If OCR fails due to missing dependencies, fallback to a simpler strategy.
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
                    "OCR dependency is missing for this PDF and OCR fallback is disabled."
                ),
            ) from exc

    elements = partition_pdf(
        filename=file_path,
        strategy=INGESTION_CONFIG.pdf_strategy_fallback,
        infer_table_structure=True,
    )

    return elements, False


# ---------------------------------------------------------------------
# Asset builders
# ---------------------------------------------------------------------

def _infer_chunk_title_from_orig_elements(orig_elements) -> str | None:
    for el in orig_elements or []:
        if _category_of(el) == "Title":
            t = _text_of(el)
            if t:
                return t[:500]
    return None


def _build_text_asset_from_chunk(chunk, source_file: str) -> dict | None:
    """
    Convert a chunk produced by `chunk_by_title` into a RAG text asset.
    """

    raw_text = _text_of(chunk)
    if not raw_text:
        return None

    metadata = _metadata_of(chunk)
    orig_elements = getattr(metadata, "orig_elements", None) or []

    element_indices = []
    page_numbers = []
    categories = []

    for el in orig_elements:
        idx = _get_runtime_element_index(el)
        if idx is not None:
            element_indices.append(idx)

        pn = _page_number_of(el)
        if pn is not None:
            page_numbers.append(pn)

        cat = _category_of(el)
        if cat:
            categories.append(cat)

    chunk_title = _infer_chunk_title_from_orig_elements(orig_elements)
    meta: dict = {
        "source_file": source_file,
        "chunking_strategy": "by_title",
        "start_element_index": min(element_indices) if element_indices else None,
        "end_element_index": max(element_indices) if element_indices else None,
        "page_start": min(page_numbers) if page_numbers else None,
        "page_end": max(page_numbers) if page_numbers else None,
        "orig_element_count": len(orig_elements),
        "orig_element_categories": sorted(set(categories)),
    }
    if chunk_title:
        meta["chunk_title"] = chunk_title
        meta["section_id"] = chunk_title

    return {
        "doc_id": str(uuid.uuid4()),
        "content_type": "text",
        "raw_content": raw_text,
        "metadata": meta,
    }


def _build_table_asset(elements, element_index, element, source_file, image_block_enabled):
    metadata = _metadata_of(element)

    table_html = getattr(metadata, "text_as_html", None)
    table_text = _text_of(element)

    raw_content = table_html or table_text
    if not raw_content:
        return None

    return {
        "doc_id": str(uuid.uuid4()),
        "content_type": "table",
        "raw_content": raw_content,
        "metadata": {
            "source_file": source_file,
            "page_number": getattr(metadata, "page_number", None),
            "table_title": _infer_nearby_title(elements, element_index),
            "text_as_html": table_html,
            "image_block_extraction_enabled": image_block_enabled,
        },
    }


def _build_image_asset(elements, element_index, element, source_file, image_block_enabled):
    metadata = _metadata_of(element)

    image_base64 = getattr(metadata, "image_base64", None)
    if not image_base64:
        return None

    return {
        "doc_id": str(uuid.uuid4()),
        "content_type": "image",
        "raw_content": image_base64,
        "metadata": {
            "source_file": source_file,
            "page_number": getattr(metadata, "page_number", None),
            "image_mime_type": getattr(metadata, "image_mime_type", None),
            "image_title": _infer_nearby_title(elements, element_index),
            "image_block_extraction_enabled": image_block_enabled,
        },
    }


# ---------------------------------------------------------------------
# Core extraction logic
# ---------------------------------------------------------------------

def _flush_text_run(extracted, text_run, source_file):
    """
    Convert a sequence of textual elements into chunked text assets.
    """
    if not text_run:
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


def _extract_partitioned_elements(elements, source_file, *, image_block_extraction_enabled):
    """
    Convert partitioned elements into multimodal RAG assets.

    Text is chunked.
    Images and tables remain independent assets.
    """

    extracted = []
    text_run = []

    for index, element in enumerate(elements):

        _set_runtime_element_metadata(element, index)

        category = _category_of(element)

        if category in TEXTUAL_CATEGORIES_TO_SKIP:
            continue

        if _is_textual_element(element):
            text_run.append(element)
            continue

        _flush_text_run(extracted, text_run, source_file)
        text_run = []

        if category == "Table":
            asset = _build_table_asset(
                elements,
                index,
                element,
                source_file,
                image_block_extraction_enabled,
            )
            if asset:
                extracted.append(asset)

        elif category == "Image":
            asset = _build_image_asset(
                elements,
                index,
                element,
                source_file,
                image_block_extraction_enabled,
            )
            if asset:
                extracted.append(asset)

    _flush_text_run(extracted, text_run, source_file)

    return extracted


# ---------------------------------------------------------------------
# File type extraction
# ---------------------------------------------------------------------

def _extract_pdf_elements(file_path: str, source_file: str) -> list[dict]:

    elements, image_enabled = _partition_pdf_with_fallback(file_path)

    return _extract_partitioned_elements(
        elements=elements,
        source_file=source_file,
        image_block_extraction_enabled=image_enabled,
    )


def _extract_docx_or_pptx_text_and_tables(file_path: str, source_file: str) -> list[dict]:

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


# ---------------------------------------------------------------------
# Embedded image fallback (DOCX / PPTX)
# ---------------------------------------------------------------------

def _extract_embedded_images_from_zip(
    file_path: str,
    source_file: str,
    media_prefix: str,
    category_name: str,
):

    extracted = []

    try:
        with zipfile.ZipFile(file_path, "r") as archive:

            media_files = [
                name
                for name in archive.namelist()
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


# ---------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------

def extract_elements(
    file_path: str,
    source_file: str,
) -> list[dict]:
    """
    Extract multimodal assets from a document.

    Supported formats:
    - PDF
    - DOCX
    - PPTX
    """

    suffix = Path(file_path).suffix.lower()

    if suffix == ".pdf":
        return _extract_pdf_elements(file_path, source_file)

    if suffix == ".docx":
        extracted = _extract_docx_or_pptx_text_and_tables(file_path, source_file)

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
        extracted = _extract_docx_or_pptx_text_and_tables(file_path, source_file)

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
