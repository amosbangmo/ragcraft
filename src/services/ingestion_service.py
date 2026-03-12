from langchain_core.documents import Document
from src.domain.project import Project
from src.infrastructure.ingestion.loader import save_uploaded_file
from src.infrastructure.ingestion.parser import parse_document
from src.infrastructure.ingestion.chunker import create_chunks


class IngestionService:
    def ingest_uploaded_file(self, project: Project, uploaded_file) -> list[Document]:
        project.path.mkdir(parents=True, exist_ok=True)

        file_path = save_uploaded_file(uploaded_file, str(project.path))
        text = parse_document(file_path)

        chunks = create_chunks(
            text=text,
            project_id=project.project_id,
            file_name=uploaded_file.name,
        )

        return chunks
