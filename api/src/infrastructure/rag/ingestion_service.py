import time
from pathlib import Path

from langchain_core.documents import Document

from infrastructure.config.config import INGESTION_CONFIG
from infrastructure.config.exceptions import (
    DocumentExtractionError,
    LLMServiceError,
    OCRDependencyError,
)
from domain.projects.buffered_document_upload import BufferedDocumentUpload
from domain.common.ingestion_diagnostics import IngestionDiagnostics
from domain.projects.project import Project
from infrastructure.rag.ingestion.loader import save_uploaded_file
from infrastructure.rag.ingestion.unstructured_extractor import extract_elements
from infrastructure.rag.ingestion.summarizer import ElementSummarizer
from infrastructure.rag.table_parsing_service import TableParsingService


def _is_ocr_dependency_error(exc: Exception) -> bool:
    message = str(exc).lower()
    return "tesseract is not installed" in message or "tesseractnotfounderror" in message


class IngestionService:
    def __init__(self):
        self.summarizer = ElementSummarizer()
        self.table_parser = TableParsingService()
        self.config = INGESTION_CONFIG

    def ingest_uploaded_file(
        self, project: Project, uploaded_file: BufferedDocumentUpload
    ) -> tuple[list[Document], list[dict], IngestionDiagnostics]:
        try:
            project.path.mkdir(parents=True, exist_ok=True)
        except Exception as exc:
            raise DocumentExtractionError(
                f"Failed to prepare project directory for upload '{uploaded_file.name}': {exc}",
                user_message="Unable to prepare the project workspace for document ingestion.",
            ) from exc

        try:
            file_path = save_uploaded_file(uploaded_file, str(project.path))
        except Exception as exc:
            raise DocumentExtractionError(
                f"Failed to save uploaded file '{uploaded_file.name}': {exc}",
                user_message=f"Unable to save the uploaded file '{uploaded_file.name}'.",
            ) from exc

        return self.ingest_file_path(
            project=project,
            file_path=file_path,
            source_file=uploaded_file.name,
        )

    def ingest_file_path(
        self,
        *,
        project: Project,
        file_path: str | Path,
        source_file: str,
    ) -> tuple[list[Document], list[dict], IngestionDiagnostics]:
        pipeline_t0 = time.perf_counter()

        t_extract0 = time.perf_counter()
        try:
            raw_elements = extract_elements(str(file_path), source_file)
        except OCRDependencyError:
            raise
        except Exception as exc:
            if _is_ocr_dependency_error(exc):
                raise OCRDependencyError(
                    f"OCR dependency error while extracting '{source_file}': {exc}",
                    user_message=(
                        "OCR dependency is missing for this document. "
                        "Install `tesseract-ocr` in the runtime image and ensure it is available in PATH."
                    ),
                ) from exc

            raise DocumentExtractionError(
                f"Failed to extract elements from '{source_file}': {exc}",
                user_message=f"Unable to extract content from '{source_file}'.",
            ) from exc

        extraction_ms = (time.perf_counter() - t_extract0) * 1000.0

        if not raw_elements:
            raise DocumentExtractionError(
                f"No extractable content found in file: {source_file}",
                user_message=f"No extractable content was found in '{source_file}'.",
            )

        summary_documents: list[Document] = []
        raw_assets: list[dict] = []

        t_summ0 = time.perf_counter()
        for element in raw_elements:
            doc_id = element["doc_id"]
            content_type = element["content_type"]
            raw_content = element["raw_content"]
            element_metadata = element.get("metadata", {})

            try:
                summary = self.summarizer.summarize(
                    content_type=content_type,
                    raw_content=raw_content,
                    metadata=element_metadata,
                )
            except Exception as exc:
                raise LLMServiceError(
                    f"Failed to summarize extracted asset for '{source_file}' (doc_id={doc_id}): {exc}",
                    user_message=(
                        f"Content was extracted from '{source_file}', "
                        "but the summarization model failed during ingestion."
                    ),
                ) from exc

            metadata = {
                "doc_id": doc_id,
                "project_id": project.project_id,
                "user_id": project.user_id,
                "file_name": source_file,
                "source_file": source_file,
                "content_type": content_type,
                **element_metadata,
            }

            if content_type == "table":
                try:
                    parsed_table = self.table_parser.parse(raw_content)
                except Exception:
                    parsed_table = {"headers": [], "rows": []}
                if (parsed_table.get("rows") or parsed_table.get("headers")):
                    metadata["structured_table"] = parsed_table

            if content_type == "image":
                for optional_key in ("surrounding_text", "image_title"):
                    v = metadata.get(optional_key)
                    if isinstance(v, str) and not v.strip():
                        metadata.pop(optional_key, None)

            summary_documents.append(
                Document(
                    page_content=summary,
                    metadata=metadata,
                )
            )

            raw_assets.append(
                {
                    "doc_id": doc_id,
                    "user_id": project.user_id,
                    "project_id": project.project_id,
                    "source_file": source_file,
                    "content_type": content_type,
                    "raw_content": raw_content,
                    "summary": summary,
                    "metadata": metadata,
                }
            )

        summarization_ms = (time.perf_counter() - t_summ0) * 1000.0
        pipeline_ms = (time.perf_counter() - pipeline_t0) * 1000.0

        diagnostics = IngestionDiagnostics(
            extraction_ms=extraction_ms,
            summarization_ms=summarization_ms,
            indexing_ms=0.0,
            total_ms=pipeline_ms,
            extracted_elements=len(raw_elements),
            generated_assets=len(raw_assets),
            errors=None,
        )

        return summary_documents, raw_assets, diagnostics
