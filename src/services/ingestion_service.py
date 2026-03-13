from pathlib import Path

from langchain_core.documents import Document

from src.domain.project import Project
from src.infrastructure.ingestion.loader import save_uploaded_file
from src.infrastructure.ingestion.unstructured_extractor import extract_elements
from src.infrastructure.ingestion.summarizer import ElementSummarizer


class IngestionService:
    def __init__(self):
        self.summarizer = ElementSummarizer()

    def ingest_uploaded_file(self, project: Project, uploaded_file) -> tuple[list[Document], list[dict]]:
        project.path.mkdir(parents=True, exist_ok=True)

        file_path = save_uploaded_file(uploaded_file, str(project.path))
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
    ) -> tuple[list[Document], list[dict]]:
        raw_elements = extract_elements(str(file_path), source_file)

        if not raw_elements:
            raise ValueError(f"No extractable content found in file: {source_file}")

        summary_documents: list[Document] = []
        raw_assets: list[dict] = []

        for element in raw_elements:
            doc_id = element["doc_id"]
            content_type = element["content_type"]
            raw_content = element["raw_content"]
            element_metadata = element.get("metadata", {})

            summary = self.summarizer.summarize(
                content_type=content_type,
                raw_content=raw_content,
                metadata=element_metadata,
            )

            metadata = {
                "doc_id": doc_id,
                "project_id": project.project_id,
                "user_id": project.user_id,
                "file_name": source_file,
                "source_file": source_file,
                "content_type": content_type,
                **element_metadata,
            }

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

        return summary_documents, raw_assets
