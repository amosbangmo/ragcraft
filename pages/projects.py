import base64

import streamlit as st

from src.ui.layout import apply_layout
from src.ui.page_header import render_hero
from src.ui.project_selector import render_project_selector
from src.ui.document_table import render_document_table
from src.auth.guards import require_authentication
from src.core.session import get_user_id
from src.core.app_state import get_app


require_authentication("pages/projects.py")
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
        if st.button("Cancel", use_container_width=True, key=f"cancel_projects_delete_{project_id}_{doc_name}"):
            st.rerun()

    with col2:
        if st.button("Delete", use_container_width=True, key=f"confirm_projects_delete_{project_id}_{doc_name}"):
            result = app.delete_project_document(
                user_id=user_id,
                project_id=project_id,
                source_file=doc_name,
            )
            st.session_state["projects_success_message"] = (
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
        if st.button("Cancel", use_container_width=True, key=f"cancel_projects_reindex_{project_id}_{doc_name}"):
            st.rerun()

    with col2:
        if st.button("Reindex", use_container_width=True, key=f"confirm_projects_reindex_{project_id}_{doc_name}"):
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

                st.session_state["projects_success_message"] = (
                    f"{doc_name}: reindexed successfully "
                    f"({replacement_info.get('deleted_assets', 0)} SQLite asset(s) replaced, "
                    f"{replacement_info.get('deleted_vectors', 0)} FAISS vector(s) replaced), "
                    f"generated {len(assets)} multimodal asset(s) {type_counts}."
                )
            except Exception as exc:
                st.session_state["projects_error_message"] = f"Failed to reindex {doc_name}: {exc}"

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


render_hero(
    badge="Projects",
    title="Manage your knowledge bases",
    subtitle="Create projects, select the active workspace and inspect ingested documents.",
)

app = get_app()
user_id = get_user_id()

if "projects_success_message" in st.session_state:
    st.success(st.session_state.pop("projects_success_message"))

if "projects_error_message" in st.session_state:
    st.error(st.session_state.pop("projects_error_message"))

st.markdown('<div class="section-card">', unsafe_allow_html=True)
st.markdown('<div class="card-title">Create a new project</div>', unsafe_allow_html=True)
st.markdown('<div class="card-subtitle">Use a short, explicit name for each workspace.</div>', unsafe_allow_html=True)

col1, col2 = st.columns([3, 1])
with col1:
    project_name = st.text_input("Project name", placeholder="e.g. annual-report-2024", key="project_name_input")
with col2:
    st.write("")
    st.write("")
    create_clicked = st.button("Create project", use_container_width=True)

if create_clicked:
    normalized_name = project_name.strip()
    if not normalized_name:
        st.warning("Please enter a project name.")
    else:
        app.create_project(user_id, normalized_name)
        st.session_state["project_id"] = normalized_name
        st.success(f"Project '{normalized_name}' created.")
st.markdown("</div>", unsafe_allow_html=True)

st.markdown('<div class="section-card">', unsafe_allow_html=True)
st.markdown('<div class="card-title">Current workspace</div>', unsafe_allow_html=True)
st.markdown('<div class="card-subtitle">The selected project is shared across all pages.</div>', unsafe_allow_html=True)
selected_project = render_project_selector(
    "Active project",
    show_create_button=False,
)
if selected_project:
    st.caption(f"Current selected project: **{selected_project}**")
st.markdown("</div>", unsafe_allow_html=True)

projects = app.list_projects(user_id)
total_documents = sum(len(app.list_project_documents(user_id, pid)) for pid in projects)

m1, m2 = st.columns(2)
with m1:
    st.metric("Projects", len(projects))
with m2:
    st.metric("Ingested documents", total_documents)

st.markdown('<div class="section-card">', unsafe_allow_html=True)
st.markdown('<div class="card-title">All projects</div>', unsafe_allow_html=True)
st.markdown('<div class="card-subtitle">Inspect each project and review its ingested documents.</div>', unsafe_allow_html=True)

if not projects:
    st.info("No project yet.")
    st.stop()

for project_id in projects:
    documents = app.get_project_document_details(user_id, project_id)
    is_current = project_id == st.session_state.get("project_id")

    with st.expander(
        f"{'✅ ' if is_current else '📂 '}{project_id} — {len(documents)} document(s)",
        expanded=is_current,
    ):
        col_a, col_b = st.columns([1, 4])

        with col_a:
            if st.button("Use project", key=f"use_{project_id}", use_container_width=True):
                st.session_state["project_id"] = project_id
                st.success(f"Selected project: {project_id}")

        with col_b:
            if is_current:
                st.caption("This is the current active project.")

        document_action = render_document_table(
            documents=documents,
            key_prefix=f"projects_{project_id}",
        )

        if document_action:
            if document_action["action"] == "delete":
                confirm_delete_document_dialog(app, user_id, project_id, document_action["doc_name"])
            elif document_action["action"] == "reindex":
                confirm_reindex_document_dialog(app, user_id, project_id, document_action["doc_name"])
            elif document_action["action"] == "inspect":
                inspect_document_dialog(app, user_id, project_id, document_action["doc_name"])

st.markdown("</div>", unsafe_allow_html=True)
