"""
Document row actions (delete / reindex / inspect). All I/O goes through the injected
:class:`~src.frontend_gateway.protocol.BackendClient` — never :class:`~src.app.ragcraft_app.RAGCraftApp`
or service containers directly.
"""

import base64

import streamlit as st

from src.ui.request_runner import (
    RUNNER_ERROR_KEY,
    clear_result_payload,
    is_request_running,
    is_runner_error_payload,
    render_result_payload,
    run_request_action,
)


REINDEXING_DOC_KEY = "reindexing_document_key"
PENDING_REINDEX_DIALOG_KEY = "pending_reindex_dialog_payload"


def _inject_document_dialog_styles():
    st.markdown(
        """
        <style>
        [data-testid="stDialog"] {
            width: 100vw !important;
        }

        [data-testid="stDialog"] > div {
            width: 100vw !important;
            max-width: 100vw !important;
            display: flex !important;
            justify-content: center !important;
            align-items: flex-start !important;
        }

        [data-testid="stDialog"] [role="dialog"] {
            width: 92vw !important;
            max-width: 1280px !important;
        }

        .rc-inspect-sticky-header {
            position: sticky;
            top: 0;
            z-index: 20;
            background: #ffffff;
            padding-top: 4px;
            padding-bottom: 10px;
            border-bottom: 1px solid rgba(15, 23, 42, 0.08);
            margin-bottom: 12px;
        }

        .rc-inspect-assets-container {
            max-height: 68vh;
            overflow-y: auto;
            padding-right: 8px;
        }

        .rc-inspect-assets-container::-webkit-scrollbar {
            width: 8px;
        }

        .rc-inspect-assets-container::-webkit-scrollbar-thumb {
            background: #cbd5e1;
            border-radius: 999px;
        }

        .rc-inspect-assets-container::-webkit-scrollbar-track {
            background: transparent;
        }

        .rc-inspect-empty {
            padding: 14px 16px;
            border-radius: 12px;
            border: 1px dashed rgba(15, 23, 42, 0.12);
            background: #ffffff;
            color: #64748b;
            text-align: center;
            margin-top: 8px;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def _render_image_asset(base64_content: str, title: str | None = None):
    try:
        image_bytes = base64.b64decode(base64_content)
        if title:
            st.markdown(f"**{title}**")
        st.image(image_bytes)
    except Exception:
        st.warning("Unable to render image asset.")


def _get_user_error_message(exc: Exception, default_message: str) -> str:
    return getattr(exc, "user_message", default_message)


def _filter_assets(assets: list[dict], selected_filter: str) -> list[dict]:
    if selected_filter == "All":
        return assets

    expected_type = selected_filter.lower()
    return [asset for asset in assets if asset.get("content_type") == expected_type]


def _build_reindexing_doc_key(project_id: str, doc_name: str) -> str:
    return f"{project_id}::{doc_name}"


def _build_reindex_request_key(project_id: str, doc_name: str) -> str:
    return f"reindex_request_running::{project_id}::{doc_name}"


def _build_reindex_result_key(project_id: str, doc_name: str) -> str:
    return f"reindex_result_payload::{project_id}::{doc_name}"


def get_reindexing_document_key() -> str | None:
    return st.session_state.get(REINDEXING_DOC_KEY)


def is_document_reindexing(project_id: str, doc_name: str) -> bool:
    request_key = _build_reindex_request_key(project_id, doc_name)
    return is_request_running(request_key) or (
        get_reindexing_document_key() == _build_reindexing_doc_key(project_id, doc_name)
    )


def set_document_reindexing(project_id: str, doc_name: str):
    st.session_state[REINDEXING_DOC_KEY] = _build_reindexing_doc_key(project_id, doc_name)


def clear_document_reindexing():
    st.session_state.pop(REINDEXING_DOC_KEY, None)


def set_pending_reindex_dialog(
    *,
    user_id: str,
    project_id: str,
    doc_name: str,
    success_message_key: str,
    error_message_key: str,
):
    st.session_state[PENDING_REINDEX_DIALOG_KEY] = {
        "user_id": user_id,
        "project_id": project_id,
        "doc_name": doc_name,
        "success_message_key": success_message_key,
        "error_message_key": error_message_key,
    }


def get_pending_reindex_dialog():
    return st.session_state.get(PENDING_REINDEX_DIALOG_KEY)


def clear_pending_reindex_dialog():
    st.session_state.pop(PENDING_REINDEX_DIALOG_KEY, None)


@st.dialog("Delete document")
def confirm_delete_document_dialog(
    backend_client,
    *,
    user_id: str,
    project_id: str,
    doc_name: str,
    success_message_key: str,
    error_message_key: str,
):
    st.warning(
        "This will remove the file from disk, delete its SQLite raw assets, "
        "remove its FAISS vectors, and refresh the project cache."
    )

    col1, col2 = st.columns(2)

    with col1:
        if st.button(
            "Cancel",
            use_container_width=True,
            key=f"cancel_delete_{project_id}_{doc_name}_{success_message_key}",
        ):
            st.rerun()

    with col2:
        if st.button(
            "Delete",
            use_container_width=True,
            key=f"confirm_delete_{project_id}_{doc_name}_{success_message_key}",
        ):
            try:
                result = backend_client.delete_project_document(
                    user_id=user_id,
                    project_id=project_id,
                    source_file=doc_name,
                )
                st.session_state[success_message_key] = result.format_delete_summary(doc_name)
            except Exception as exc:
                st.session_state[error_message_key] = _get_user_error_message(
                    exc,
                    f"Failed to delete '{doc_name}'.",
                )

            st.rerun()


@st.dialog("Reindex document")
def confirm_reindex_document_dialog(
    backend_client,
    *,
    user_id: str,
    project_id: str,
    doc_name: str,
    success_message_key: str,
    error_message_key: str,
):
    request_key = _build_reindex_request_key(project_id, doc_name)
    result_key = _build_reindex_result_key(project_id, doc_name)

    st.info(
        "This will reprocess the file already stored on disk, rebuild its SQLite assets, "
        "refresh its FAISS vectors, and invalidate the project retrieval cache."
    )

    def _run_reindex():
        return backend_client.reindex_project_document(
            user_id=user_id,
            project_id=project_id,
            source_file=doc_name,
        )

    def _map_reindex_error(exc: Exception) -> str:
        return _get_user_error_message(
            exc,
            f"Failed to reindex '{doc_name}'.",
        )

    def _render_reindex_result(result):
        st.session_state[success_message_key] = result.format_reindex_success_message(doc_name)

        clear_result_payload(result_key)
        clear_document_reindexing()
        clear_pending_reindex_dialog()
        st.rerun()

    trigger_reindex = False

    col1, col2 = st.columns(2)

    with col1:
        if st.button(
            "Cancel",
            use_container_width=True,
            key=f"cancel_reindex_{project_id}_{doc_name}_{success_message_key}",
            disabled=is_request_running(request_key),
        ):
            clear_result_payload(result_key)
            clear_pending_reindex_dialog()
            clear_document_reindexing()
            st.rerun()

    with col2:
        trigger_reindex = st.button(
            "Reindex",
            use_container_width=True,
            key=f"confirm_reindex_{project_id}_{doc_name}_{success_message_key}",
            disabled=is_request_running(request_key),
        )

    if trigger_reindex:
        set_document_reindexing(project_id, doc_name)
        set_pending_reindex_dialog(
            user_id=user_id,
            project_id=project_id,
            doc_name=doc_name,
            success_message_key=success_message_key,
            error_message_key=error_message_key,
        )

    run_request_action(
        request_key=request_key,
        result_key=result_key,
        trigger=trigger_reindex,
        can_run=True,
        action=_run_reindex,
        spinner_text=f"Reindexing {doc_name}...",
        error_mapper=_map_reindex_error,
    )

    render_result_payload(
        result_key=result_key,
        on_success=_render_reindex_result,
    )

    result_payload = st.session_state.get(result_key)
    if is_runner_error_payload(result_payload):
        raw_err = result_payload.get(RUNNER_ERROR_KEY)
        st.session_state[error_message_key] = (
            raw_err if isinstance(raw_err, str) else str(raw_err)
        )
        clear_result_payload(result_key)
        clear_document_reindexing()
        clear_pending_reindex_dialog()
        st.rerun()


@st.dialog("Inspect document")
def inspect_document_dialog(
    backend_client,
    *,
    user_id: str,
    project_id: str,
    doc_name: str,
):
    _inject_document_dialog_styles()

    try:
        assets = backend_client.get_document_assets(
            user_id=user_id,
            project_id=project_id,
            source_file=doc_name,
        )
    except Exception as exc:
        st.error(_get_user_error_message(exc, f"Unable to inspect '{doc_name}'."))
        return

    if not assets:
        st.info("No indexed assets found for this document.")
        return

    text_count = sum(1 for asset in assets if asset.get("content_type") == "text")
    table_count = sum(1 for asset in assets if asset.get("content_type") == "table")
    image_count = sum(1 for asset in assets if asset.get("content_type") == "image")

    filter_options = ["All", "Text", "Table", "Image"]
    selected_filter = st.segmented_control(
        "Filter assets",
        options=filter_options,
        default="All",
        selection_mode="single",
        key=f"inspect_filter_{project_id}_{doc_name}",
    )

    filtered_assets = _filter_assets(assets, selected_filter or "All")

    st.markdown('<div class="rc-inspect-sticky-header">', unsafe_allow_html=True)
    st.markdown(f"### {doc_name}")
    st.caption("Review the indexed assets currently stored for this document.")

    c1, c2, c3, c4, c5 = st.columns(5)
    with c1:
        st.metric("Assets", len(assets))
    with c2:
        st.metric("Texts", text_count)
    with c3:
        st.metric("Tables", table_count)
    with c4:
        st.metric("Images", image_count)
    with c5:
        st.metric("Visible", len(filtered_assets))

    st.markdown("</div>", unsafe_allow_html=True)

    if not filtered_assets:
        st.markdown(
            '<div class="rc-inspect-empty">No assets match the selected filter.</div>',
            unsafe_allow_html=True,
        )
        return

    st.markdown('<div class="rc-inspect-assets-container">', unsafe_allow_html=True)

    for index, asset in enumerate(filtered_assets, start=1):
        content_type = asset.get("content_type", "unknown")
        metadata = asset.get("metadata", {}) or {}
        summary = asset.get("summary", "") or ""
        raw_content = asset.get("raw_content", "") or ""
        page_number = metadata.get("page_number")
        page_start = metadata.get("page_start")
        page_end = metadata.get("page_end")
        table_title = metadata.get("table_title")
        image_title = metadata.get("image_title")
        chunk_title = metadata.get("chunk_title")
        start_element_index = metadata.get("start_element_index")
        end_element_index = metadata.get("end_element_index")

        title_parts = [f"Asset {index} — {content_type}"]

        if table_title:
            title_parts.append(f"— {table_title}")
        if image_title:
            title_parts.append(f"— {image_title}")
        if chunk_title:
            title_parts.append(f"— {chunk_title}")

        if page_number is not None:
            title_parts.append(f"— page {page_number}")
        elif page_start is not None and page_end is not None:
            if page_start == page_end:
                title_parts.append(f"— page {page_start}")
            else:
                title_parts.append(f"— pages {page_start}-{page_end}")

        if content_type == "text" and start_element_index is not None and end_element_index is not None:
            if start_element_index == end_element_index:
                title_parts.append(f"— element {start_element_index}")
            else:
                title_parts.append(f"— elements {start_element_index}-{end_element_index}")

        with st.expander(" ".join(title_parts)):
            if summary:
                st.markdown("**Summary**")
                st.write(summary)

            st.markdown("**Metadata**")
            st.json(metadata)

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

    st.markdown("</div>", unsafe_allow_html=True)


def handle_document_action(
    backend_client,
    *,
    action_payload: dict | None,
    user_id: str,
    project_id: str,
    success_message_key: str,
    error_message_key: str | None = None,
):
    resolved_error_key = error_message_key or "document_action_error_message"

    pending_reindex = get_pending_reindex_dialog()
    if pending_reindex:
        confirm_reindex_document_dialog(
            backend_client,
            user_id=pending_reindex["user_id"],
            project_id=pending_reindex["project_id"],
            doc_name=pending_reindex["doc_name"],
            success_message_key=pending_reindex["success_message_key"],
            error_message_key=pending_reindex["error_message_key"],
        )
        return

    if not action_payload:
        return

    action = action_payload.get("action")
    doc_name = action_payload.get("doc_name")

    if not doc_name:
        return

    if action == "delete":
        confirm_delete_document_dialog(
            backend_client,
            user_id=user_id,
            project_id=project_id,
            doc_name=doc_name,
            success_message_key=success_message_key,
            error_message_key=resolved_error_key,
        )
        return

    if action == "reindex":
        confirm_reindex_document_dialog(
            backend_client,
            user_id=user_id,
            project_id=project_id,
            doc_name=doc_name,
            success_message_key=success_message_key,
            error_message_key=resolved_error_key,
        )
        return

    if action == "inspect":
        inspect_document_dialog(
            backend_client,
            user_id=user_id,
            project_id=project_id,
            doc_name=doc_name,
        )
