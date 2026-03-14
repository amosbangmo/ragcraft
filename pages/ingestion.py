import streamlit as st

from src.ui.layout import apply_layout
from src.ui.page_header import render_page_header
from src.ui.document_table import render_document_table
from src.ui.document_actions import handle_document_action
from src.auth.guards import require_authentication


require_authentication("pages/ingestion.py")
apply_layout()


st.set_page_config(
    page_title="Ingestion | RAGCraft",
    page_icon="📄",
    layout="wide",
)

header = render_page_header(
    badge="Ingestion",
    title="Add documents to a project",
    subtitle="Upload PDF, DOCX or PPTX files and turn them into searchable multimodal assets.",
    selector_label="Project for ingestion",
)

app = header["app"]
user_id = header["user_id"]
project_id = header["project_id"]

if not project_id:
    st.stop()

if "ingestion_success_message" in st.session_state:
    st.success(st.session_state.pop("ingestion_success_message"))

if "ingestion_error_message" in st.session_state:
    st.error(st.session_state.pop("ingestion_error_message"))

documents = app.list_project_documents(user_id, project_id)

st.metric("Existing documents", len(documents))

uploaded_files = st.file_uploader(
    "Upload documents",
    type=["pdf", "docx", "pptx"],
    accept_multiple_files=True,
)

if uploaded_files:
    for uploaded_file in uploaded_files:
        try:
            with st.spinner(f"Processing {uploaded_file.name}..."):
                result = app.ingest_uploaded_file(user_id, project_id, uploaded_file)

            assets = result["raw_assets"]
            replacement_info = result["replacement_info"]

            type_counts: dict[str, int] = {}
            for asset in assets:
                asset_type = asset["content_type"]
                type_counts[asset_type] = type_counts.get(asset_type, 0) + 1

            deleted_assets = replacement_info.get("deleted_assets", 0)
            deleted_vectors = replacement_info.get("deleted_vectors", 0)

            if deleted_assets or deleted_vectors:
                st.success(
                    f"{uploaded_file.name}: replaced previous ingestion "
                    f"({deleted_assets} SQLite asset(s) removed, {deleted_vectors} FAISS vector(s) removed), "
                    f"then processed {len(assets)} multimodal asset(s) {type_counts}"
                )
            else:
                st.success(
                    f"{uploaded_file.name}: processed {len(assets)} multimodal asset(s) {type_counts}"
                )

        except Exception as exc:
            error_message = str(exc)

            if "tesseract is not installed" in error_message.lower():
                st.error(
                    f"Failed to process {uploaded_file.name}: "
                    "Tesseract OCR is required for hi_res PDF parsing. "
                    "Install `tesseract-ocr` in the runtime image and ensure it is available in PATH."
                )
            else:
                st.error(f"Failed to process {uploaded_file.name}: {exc}")

updated_documents = app.get_project_document_details(user_id, project_id)

st.markdown('<div class="section-card">', unsafe_allow_html=True)
st.markdown('<div class="card-title">Documents in current project</div>', unsafe_allow_html=True)
st.markdown(
    '<div class="card-subtitle">Review and manage files already indexed in this workspace.</div>',
    unsafe_allow_html=True,
)

document_action = render_document_table(
    documents=updated_documents,
    key_prefix=f"ingestion_{project_id}",
)

handle_document_action(
    app,
    action_payload=document_action,
    user_id=user_id,
    project_id=project_id,
    success_message_key="ingestion_success_message",
    error_message_key="ingestion_error_message",
)

st.markdown("</div>", unsafe_allow_html=True)
