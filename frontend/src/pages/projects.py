"""
Projects workspace UI. All backend access goes through :class:`~services.api_client.BackendClient`
(:func:`~services.api_client.get_backend_client`); set ``RAGCRAFT_BACKEND_CLIENT=http``
to use FastAPI as system of record.
"""

import streamlit as st

from components.shared.document_actions import handle_document_action
from components.shared.document_table import render_document_table
from components.shared.layout import apply_layout
from components.shared.page_header import render_page_header
from components.shared.project_selector import render_project_selector
from infrastructure.auth.guards import require_authentication
from services.api_client import BackendClient

st.set_page_config(
    page_title="Projects | RAGCraft",
    page_icon="📁",
    layout="wide",
)

require_authentication("pages/projects.py")
apply_layout()


header = render_page_header(
    badge="Projects",
    title="Manage your knowledge bases",
    subtitle="Create projects, select the active workspace and inspect ingested documents.",
    show_project_selector=False,
)

client: BackendClient = header["backend_client"]
user_id = str(header["user_id"])
project_id = str(header["project_id"]) if header["project_id"] else None

if "projects_success_message" in st.session_state:
    st.success(st.session_state.pop("projects_success_message"))

if "projects_error_message" in st.session_state:
    st.error(st.session_state.pop("projects_error_message"))

st.markdown('<div class="section-card">', unsafe_allow_html=True)
st.markdown('<div class="card-title">Create a new project</div>', unsafe_allow_html=True)
st.markdown(
    '<div class="card-subtitle">Use a short, explicit name for each workspace.</div>',
    unsafe_allow_html=True,
)

col1, col2 = st.columns([3, 1])
with col1:
    project_name = st.text_input(
        "Project name", placeholder="e.g. annual-report-2024", key="project_name_input"
    )
with col2:
    st.write("")
    st.write("")
    create_clicked = st.button("Create project", use_container_width=True)

if create_clicked:
    normalized_name = project_name.strip()
    if not normalized_name:
        st.warning("Please enter a project name.")
    else:
        client.create_project(user_id, normalized_name)
        st.session_state["project_id"] = normalized_name
        st.success(f"Project '{normalized_name}' created.")
st.markdown("</div>", unsafe_allow_html=True)

st.markdown('<div class="section-card">', unsafe_allow_html=True)
st.markdown('<div class="card-title">Current workspace</div>', unsafe_allow_html=True)
st.markdown(
    '<div class="card-subtitle">The selected project is shared across all pages.</div>',
    unsafe_allow_html=True,
)
selected_project = render_project_selector(
    "Active project",
    show_create_button=False,
)
if selected_project:
    st.caption(f"Current selected project: **{selected_project}**")
st.markdown("</div>", unsafe_allow_html=True)

projects = client.list_projects(user_id)
active_docs = (
    len(client.list_project_documents(user_id, selected_project)) if selected_project else 0
)

m1, m2 = st.columns(2)
with m1:
    st.metric("Projects", len(projects))
with m2:
    st.metric("Ingested documents", active_docs)

st.markdown('<div class="section-card">', unsafe_allow_html=True)
st.markdown('<div class="card-title">All projects</div>', unsafe_allow_html=True)
st.markdown(
    '<div class="card-subtitle">Inspect each project and review its ingested documents.</div>',
    unsafe_allow_html=True,
)

if not projects:
    st.info("No project yet.")
    st.stop()

for project_id in projects:
    documents = client.get_project_document_details(user_id, project_id)
    is_current = project_id == st.session_state.get("project_id")
    retrieval_label = client.retrieval_preset_label_for_project(user_id, project_id)

    with st.expander(
        f"{'✅ ' if is_current else '📂 '}{project_id} — {len(documents)} document(s) · retrieval: {retrieval_label}",
        expanded=is_current,
    ):
        document_action = render_document_table(
            documents=documents,
            key_prefix=f"projects_{project_id}",
        )

        handle_document_action(
            client,
            action_payload=document_action,
            user_id=user_id,
            project_id=project_id,
            success_message_key="projects_success_message",
            error_message_key="projects_error_message",
        )

st.markdown("</div>", unsafe_allow_html=True)
