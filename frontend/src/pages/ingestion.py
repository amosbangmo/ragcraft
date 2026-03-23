"""
Ingestion UI. All project/document operations use :class:`~src.frontend_gateway.protocol.BackendClient`
(``RAGCRAFT_BACKEND_CLIENT=http`` → FastAPI).
"""

import streamlit as st

from services.protocol import BackendClient
from components.shared.layout import apply_layout
from components.shared.page_header import render_page_header
from components.shared.document_table import render_document_table
from components.shared.document_actions import handle_document_action
from components.shared.request_runner import (
    is_request_running,
    run_request_action,
    render_result_payload,
)
from infrastructure.auth.guards import require_authentication


st.set_page_config(
    page_title="Ingestion | RAGCraft",
    page_icon="📄",
    layout="wide",
)

require_authentication("pages/ingestion.py")
apply_layout()

INGESTION_REQUEST_KEY = "ingestion_request_running"
INGESTION_RESULT_KEY = "ingestion_result_payload"


header = render_page_header(
    badge="Ingestion",
    title="Add documents to a project",
    subtitle="Upload PDF, DOCX or PPTX files and turn them into searchable multimodal assets.",
    selector_label="Project for ingestion",
)

client: BackendClient = header["backend_client"]
user_id = str(header["user_id"])
project_id = str(header["project_id"]) if header["project_id"] else None

if not project_id:
    st.stop()

if "ingestion_success_message" in st.session_state:
    st.success(st.session_state.pop("ingestion_success_message"))

if "ingestion_error_message" in st.session_state:
    st.error(st.session_state.pop("ingestion_error_message"))

documents = client.list_project_documents(user_id, project_id)

st.metric("Existing documents", len(documents))

uploaded_files = st.file_uploader(
    "Upload documents",
    type=["pdf", "docx", "pptx"],
    accept_multiple_files=True,
)

process_clicked = st.button(
    "Process uploaded documents",
    use_container_width=True,
    disabled=is_request_running(INGESTION_REQUEST_KEY),
)


def _run_ingestion():
    results: list[dict] = []

    for uploaded_file in uploaded_files:
        result = client.ingest_uploaded_file(user_id, project_id, uploaded_file)
        results.append(
            {
                "file_name": uploaded_file.name,
                "success_message": result.format_ingestion_success_message(uploaded_file.name),
                "diagnostics": result.diagnostics.to_dict(),
            }
        )

    return results


def _map_ingestion_error(exc: Exception) -> str:
    error_message = str(exc)

    if "tesseract is not installed" in error_message.lower():
        return (
            "Tesseract OCR is required for hi_res PDF parsing. "
            "Install `tesseract-ocr` in the runtime image and ensure it is available in PATH."
        )

    return f"Failed to process uploaded documents: {exc}"


def _render_ingestion_result(results: list[dict]):
    if not results:
        st.info("No document was processed.")
        return

    for item in results:
        file_name = item["file_name"]
        st.success(item["success_message"])

        diagnostics = item.get("diagnostics") or {}
        if diagnostics:
            with st.expander(f"Pipeline diagnostics — {file_name}", expanded=False):
                m1, m2, m3, m4 = st.columns(4)
                with m1:
                    st.metric("Total time (ms)", f"{diagnostics.get('total_ms', 0):.0f}")
                with m2:
                    st.metric("Extraction (ms)", f"{diagnostics.get('extraction_ms', 0):.0f}")
                with m3:
                    st.metric("Summarization (ms)", f"{diagnostics.get('summarization_ms', 0):.0f}")
                with m4:
                    st.metric("Indexing (ms)", f"{diagnostics.get('indexing_ms', 0):.0f}")
                c1, c2 = st.columns(2)
                with c1:
                    st.metric("Extracted elements", diagnostics.get("extracted_elements", 0))
                with c2:
                    st.metric("Generated assets", diagnostics.get("generated_assets", 0))
                err_list = diagnostics.get("errors") or []
                if err_list:
                    st.warning("Warnings: " + "; ".join(str(e) for e in err_list))


if process_clicked and not uploaded_files:
    st.warning("Please upload at least one document.")
else:
    run_request_action(
        request_key=INGESTION_REQUEST_KEY,
        result_key=INGESTION_RESULT_KEY,
        trigger=process_clicked,
        can_run=bool(uploaded_files),
        action=_run_ingestion,
        spinner_text="Processing uploaded documents...",
        error_mapper=_map_ingestion_error,
    )

render_result_payload(
    result_key=INGESTION_RESULT_KEY,
    on_success=_render_ingestion_result,
)

updated_documents = client.get_project_document_details(user_id, project_id)

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
    client,
    action_payload=document_action,
    user_id=user_id,
    project_id=project_id,
    success_message_key="ingestion_success_message",
    error_message_key="ingestion_error_message",
)

st.markdown("</div>", unsafe_allow_html=True)
