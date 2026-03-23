"""
Summary / recall search UI. Uses :class:`~services.protocol.BackendClient.search_project_summaries``.
"""

import streamlit as st

from components.shared.layout import apply_layout
from components.shared.page_header import render_page_header
from components.shared.retrieval_settings_panel import (
    render_retrieval_settings_panel,
    retrieval_settings_to_request_dict,
)
from infrastructure.auth.guards import require_authentication
from services.protocol import BackendClient
from services.ui_errors import (
    DocStoreError,
    VectorStoreError,
    get_user_error_message,
)
from services.view_models import RetrievalFilters

st.set_page_config(
    page_title="Search | RAGCraft",
    page_icon="🔎",
    layout="wide",
)

require_authentication("pages/search.py")
apply_layout()


header = render_page_header(
    badge="Search",
    title="Inspect vector retrieval",
    subtitle="Debug summary retrieval from FAISS before raw asset rehydration.",
    selector_label="Project for search",
)

client: BackendClient = header["backend_client"]
user_id = str(header["user_id"])
project_id = str(header["project_id"]) if header["project_id"] else None

if not project_id:
    st.stop()

retrieval_settings = render_retrieval_settings_panel(
    title="Retrieval settings",
    expanded=False,
    user_id=user_id,
    project_id=project_id,
    backend_client=client,
)

query = st.text_input("Search query", placeholder="Type a semantic query...")

with st.expander("Metadata filters (optional)", expanded=False):
    use_filters = st.toggle("Apply metadata filters", value=False)
    doc_names = client.list_project_documents(user_id, project_id)
    sel_sources = st.multiselect("Source files", options=doc_names, default=[])
    sel_types = st.multiselect("Content types", options=["text", "table", "image"], default=[])
    c1, c2 = st.columns(2)
    with c1:
        pstart = st.number_input("Page range start (0 = ignore)", min_value=0, value=0, step=1)
    with c2:
        pend = st.number_input("Page range end (0 = ignore)", min_value=0, value=0, step=1)


def _search_filters() -> RetrievalFilters | None:
    if not use_filters:
        return None
    ps = int(pstart) if int(pstart) > 0 else None
    pe = int(pend) if int(pend) > 0 else None
    if (ps is None) != (pe is None):
        st.warning("Set both page start and end, or leave both at 0.")
        ps, pe = None, None
    elif ps is not None and pe is not None and ps > pe:
        st.warning("Page range start cannot be greater than end.")
        ps, pe = None, None
    f = RetrievalFilters(
        source_files=list(sel_sources),
        content_types=list(sel_types),
        page_start=ps,
        page_end=pe,
    )
    return f if not f.is_empty() else None


if query:
    try:
        filters = _search_filters()
        with st.spinner("Searching summaries..."):
            preview = client.search_project_summaries(
                user_id=user_id,
                project_id=project_id,
                query=query,
                filters=filters,
                retrieval_settings=retrieval_settings_to_request_dict(retrieval_settings),
                enable_query_rewrite_override=retrieval_settings.enable_query_rewrite,
                enable_hybrid_retrieval_override=retrieval_settings.enable_hybrid_retrieval,
            )

        if preview is None:
            st.info("No summaries found.")
            st.stop()

        docs = preview["recalled_summary_docs"]

        st.caption(
            f"Mode: **{preview['retrieval_mode']}** · "
            f"Rewrite: **{'on' if preview['query_rewrite_enabled'] else 'off'}** · "
            f"Hybrid: **{'on' if preview['hybrid_retrieval_enabled'] else 'off'}** · "
            f"Adaptive: **{'on' if preview['use_adaptive_retrieval'] else 'off'}**"
        )
        if (
            preview.get("rewritten_question")
            and preview["rewritten_question"].strip() != query.strip()
        ):
            st.caption(f"Retrieval query: {preview['rewritten_question']}")

        st.metric("Retrieved summaries", len(docs))
        st.markdown("### Retrieved summaries")

        for doc in docs:
            file_name = doc.metadata.get("file_name", "unknown")
            doc_id = doc.metadata.get("doc_id", "?")
            content_type = doc.metadata.get("content_type", "unknown")

            st.markdown(
                f"""
                <div class="source-card">
                    <div class="source-title">{file_name} — {content_type} — doc_id {doc_id}</div>
                    <div class="source-preview">{doc.page_content}</div>
                </div>
                """,
                unsafe_allow_html=True,
            )
    except VectorStoreError as exc:
        st.error(get_user_error_message(exc, "Unable to query the FAISS index for this search."))
    except DocStoreError as exc:
        st.error(get_user_error_message(exc, "Unable to run lexical retrieval for this search."))
    except Exception as exc:
        st.error(get_user_error_message(exc, f"Unexpected error while searching: {exc}"))
