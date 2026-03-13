import base64

import streamlit as st


def _render_image_asset(base64_content: str, title: str | None = None):
    try:
        image_bytes = base64.b64decode(base64_content)
        if title:
            st.markdown(f"**{title}**")
        st.image(image_bytes)
    except Exception:
        st.warning("Unable to render image asset.")


@st.dialog("Delete document")
def confirm_delete_document_dialog(
    app,
    *,
    user_id: str,
    project_id: str,
    doc_name: str,
    success_message_key: str,
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
            result = app.delete_project_document(
                user_id=user_id,
                project_id=project_id,
                source_file=doc_name,
            )
            st.session_state[success_message_key] = (
                f"{doc_name}: file deleted={result['file_deleted']}, "
                f"SQLite assets removed={result['deleted_assets']}, "
                f"FAISS vectors removed={result['deleted_vectors']}."
            )
            st.rerun()


@st.dialog("Reindex document")
def confirm_reindex_document_dialog(
    app,
    *,
    user_id: str,
    project_id: str,
    doc_name: str,
    success_message_key: str,
    error_message_key: str,
):
    st.info(
        "This will reprocess the file already stored on disk, rebuild its SQLite assets, "
        "refresh its FAISS vectors, and invalidate the project retrieval cache."
    )

    col1, col2 = st.columns(2)

    with col1:
        if st.button(
            "Cancel",
            use_container_width=True,
            key=f"cancel_reindex_{project_id}_{doc_name}_{success_message_key}",
        ):
            st.rerun()

    with col2:
        if st.button(
            "Reindex",
            use_container_width=True,
            key=f"confirm_reindex_{project_id}_{doc_name}_{success_message_key}",
        ):
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

                st.session_state[success_message_key] = (
                    f"{doc_name}: reindexed successfully "
                    f"({replacement_info.get('deleted_assets', 0)} SQLite asset(s) replaced, "
                    f"{replacement_info.get('deleted_vectors', 0)} FAISS vector(s) replaced), "
                    f"generated {len(assets)} multimodal asset(s) {type_counts}."
                )
            except Exception as exc:
                st.session_state[error_message_key] = f"Failed to reindex {doc_name}: {exc}"

            st.rerun()


@st.dialog("Inspect document")
def inspect_document_dialog(
    app,
    *,
    user_id: str,
    project_id: str,
    doc_name: str,
):
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


def handle_document_action(
    app,
    *,
    action_payload: dict | None,
    user_id: str,
    project_id: str,
    success_message_key: str,
    error_message_key: str | None = None,
):
    if not action_payload:
        return

    action = action_payload.get("action")
    doc_name = action_payload.get("doc_name")

    if not doc_name:
        return

    if action == "delete":
        confirm_delete_document_dialog(
            app,
            user_id=user_id,
            project_id=project_id,
            doc_name=doc_name,
            success_message_key=success_message_key,
        )
        return

    if action == "reindex":
        confirm_reindex_document_dialog(
            app,
            user_id=user_id,
            project_id=project_id,
            doc_name=doc_name,
            success_message_key=success_message_key,
            error_message_key=error_message_key or "document_action_error_message",
        )
        return

    if action == "inspect":
        inspect_document_dialog(
            app,
            user_id=user_id,
            project_id=project_id,
            doc_name=doc_name,
        )
