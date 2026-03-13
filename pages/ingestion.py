import streamlit as st

from src.ui.layout import apply_layout
from src.ui.page_header import render_page_header
from src.auth.guards import require_authentication


require_authentication("pages/ingestion.py")
apply_layout()


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
                assets = app.ingest_uploaded_file(user_id, project_id, uploaded_file)

            type_counts: dict[str, int] = {}
            for asset in assets:
                asset_type = asset["content_type"]
                type_counts[asset_type] = type_counts.get(asset_type, 0) + 1

            st.success(
                f"{uploaded_file.name}: {len(assets)} multimodal asset(s) processed "
                f"({type_counts})"
            )

        except Exception as exc:
            error_message = str(exc)

            if "tesseract is not installed" in error_message.lower():
                st.error(
                    f"Failed to process {uploaded_file.name}: Tesseract OCR is required for hi_res PDF parsing. "
                    "Install `tesseract-ocr` in the runtime image and ensure it is available in PATH."
                )
            else:
                st.error(f"Failed to process {uploaded_file.name}: {exc}")

updated_documents = app.list_project_documents(user_id, project_id)

st.markdown('<div class="section-card">', unsafe_allow_html=True)
st.markdown('<div class="card-title">Documents in current project</div>', unsafe_allow_html=True)
st.markdown('<div class="card-subtitle">These files are currently available in the active workspace.</div>', unsafe_allow_html=True)

if updated_documents:
    for doc_name in updated_documents:
        st.markdown(f"- {doc_name}")
else:
    st.caption("No document ingested yet.")

st.markdown("</div>", unsafe_allow_html=True)
