from langchain_core.documents import Document

from src.domain.project import Project
from src.infrastructure.ingestion.loader import save_uploaded_file
from src.infrastructure.ingestion.unstructured_extractor import extract_elements
from src.infrastructure.ingestion.summarizer import ElementSummarizer


class IngestionService:
    def __init__(self):
        self.summarizer = ElementSummarizer()

    def ingest_uploaded_file(self, project: Project, uploaded_file) -> tuple[list[Document], list[dict]]:
        """
        Returns:
        - summary_documents: LangChain Documents to index in FAISS
        - raw_assets: raw multimodal assets to persist in SQLite docstore
        """
        project.path.mkdir(parents=True, exist_ok=True)

        file_path = save_uploaded_file(uploaded_file, str(project.path))
        raw_elements = extract_elements(file_path, uploaded_file.name)

        if not raw_elements:
            raise ValueError(f"No extractable content found in file: {uploaded_file.name}")

        summary_documents: list[Document] = []
        raw_assets: list[dict] = []

        for element in raw_elements:
            doc_id = element["doc_id"]
            content_type = element["content_type"]
            raw_content = element["raw_content"]
            element_metadata = element.get("metadata", {})

            summary = self.summarizer.summarize(content_type, raw_content)

            metadata = {
                "doc_id": doc_id,
                "project_id": project.project_id,
                "user_id": project.user_id,
                "file_name": uploaded_file.name,
                "source_file": uploaded_file.name,
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
                    "source_file": uploaded_file.name,
                    "content_type": content_type,
                    "raw_content": raw_content,
                    "summary": summary,
                    "metadata": metadata,
                }
            )

        return summary_documents, raw_assets
