import base64

import streamlit as st

from src.ui.layout import apply_layout
from src.ui.page_header import render_page_header
from src.ui.document_table import render_document_table
from src.auth.guards import require_authentication


require_authentication("pages/ingestion.py")
apply_layout()


def _render_image_asset(base64_content: str, title: str | None = None):
    try:
        image_bytes = base64.b64decode(base64_content)
        if title:
            st.markdown(f"**{title}**")
        st.image(image_bytes)
    except Exception:
        st.warning("Unable to render image asset.")


@st.dialog("Delete document")
def confirm_delete_document_dialog(app, user_id: str, project_id: str, doc_name: str):
    st.warning(
        "This will remove the file from disk, delete its SQLite raw assets, "
        "remove its FAISS vectors, and refresh the project cache."
    )

    col1, col2 = st.columns(2)

    with col1:
        if st.button("Cancel", use_container_width=True, key=f"cancel_delete_{doc_name}"):
            st.rerun()

    with col2:
        if st.button("Delete", use_container_width=True, key=f"confirm_delete_{doc_name}"):
            result = app.delete_project_document(
                user_id=user_id,
                project_id=project_id,
                source_file=doc_name,
            )
            st.session_state["ingestion_success_message"] = (
                f"{doc_name}: file deleted={result['file_deleted']}, "
                f"SQLite assets removed={result['deleted_assets']}, "
                f"FAISS vectors removed={result['deleted_vectors']}."
            )
            st.rerun()


@st.dialog("Reindex document")
def confirm_reindex_document_dialog(app, user_id: str, project_id: str, doc_name: str):
    st.info(
        "This will reprocess the file already stored on disk, rebuild its SQLite assets, "
        "refresh its FAISS vectors, and invalidate the project retrieval cache."
    )

    col1, col2 = st.columns(2)

    with col1:
        if st.button("Cancel", use_container_width=True, key=f"cancel_reindex_{doc_name}"):
            st.rerun()

    with col2:
        if st.button("Reindex", use_container_width=True, key=f"confirm_reindex_{doc_name}"):
            try:
                result = app.reindex_project_document(
                    user_id=user_id,
                    project_id=project_id,
                    source_file=doc_name,
                )
                assets = result["raw_assets"]
                replacement_info = result["replacement_info"]

                type_counts: dict[str, int] = {}
                for asset in assets:
                    asset_type = asset["content_type"]
                    type_counts[asset_type] = type_counts.get(asset_type, 0) + 1

                st.session_state["ingestion_success_message"] = (
                    f"{doc_name}: reindexed successfully "
                    f"({replacement_info.get('deleted_assets', 0)} SQLite asset(s) replaced, "
                    f"{replacement_info.get('deleted_vectors', 0)} FAISS vector(s) replaced), "
                    f"generated {len(assets)} multimodal asset(s) {type_counts}."
                )
            except Exception as exc:
                st.session_state["ingestion_error_message"] = f"Failed to reindex {doc_name}: {exc}"

            st.rerun()


@st.dialog("Inspect document")
def inspect_document_dialog(app, user_id: str, project_id: str, doc_name: str):
    assets = app.get_document_assets(
        user_id=user_id,
        project_id=project_id,
        source_file=doc_name,
    )

    st.markdown(f"### {doc_name}")
    st.caption("Review the indexed assets currently stored for this document.")

    if not assets:
        st.info("No indexed assets found for this document.")
        return

    text_count = sum(1 for asset in assets if asset.get("content_type") == "text")
    table_count = sum(1 for asset in assets if asset.get("content_type") == "table")
    image_count = sum(1 for asset in assets if asset.get("content_type") == "image")

    c1, c2, c3, c4 = st.columns(4)
    with c1:
        st.metric("Assets", len(assets))
    with c2:
        st.metric("Texts", text_count)
    with c3:
        st.metric("Tables", table_count)
    with c4:
        st.metric("Images", image_count)

    for index, asset in enumerate(assets, start=1):
        content_type = asset.get("content_type", "unknown")
        metadata = asset.get("metadata", {}) or {}
        summary = asset.get("summary", "") or ""
        raw_content = asset.get("raw_content", "") or ""
        page_number = metadata.get("page_number")
        table_title = metadata.get("table_title")
        image_title = metadata.get("image_title")

        title_parts = [f"Asset {index} — {content_type}"]

        if table_title:
            title_parts.append(f"— {table_title}")
        if image_title:
            title_parts.append(f"— {image_title}")
        if page_number is not None:
            title_parts.append(f"— page {page_number}")

        with st.expander(" ".join(title_parts)):
            if summary:
                st.markdown("**Summary**")
                st.write(summary)

            if content_type == "text":
                st.markdown("**Raw text**")
                st.write(raw_content[:4000])
                continue

            if content_type == "table":
                st.markdown("**Raw table**")
                st.markdown(raw_content, unsafe_allow_html=True)
                continue

            if content_type == "image":
                st.markdown("**Image preview**")
                _render_image_asset(raw_content, title=image_title)
                continue

            st.write(raw_content[:4000])


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

if document_action:
    if document_action["action"] == "delete":
        confirm_delete_document_dialog(app, user_id, project_id, document_action["doc_name"])
    elif document_action["action"] == "reindex":
        confirm_reindex_document_dialog(app, user_id, project_id, document_action["doc_name"])
    elif document_action["action"] == "inspect":
        inspect_document_dialog(app, user_id, project_id, document_action["doc_name"])

st.markdown("</div>", unsafe_allow_html=True)
