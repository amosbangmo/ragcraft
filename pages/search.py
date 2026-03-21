import streamlit as st

from typing import cast
from src.app.ragcraft_app import RAGCraftApp
from src.domain.retrieval_filters import (
    RetrievalFilters,
    filter_summary_documents_by_filters,
    vector_search_fetch_k,
)
from src.ui.layout import apply_layout
from src.ui.page_header import render_page_header
from src.auth.guards import require_authentication
from src.core.error_utils import get_user_error_message
from src.core.exceptions import VectorStoreError


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

app = cast(RAGCraftApp, header["app"])
user_id = str(header["user_id"])
project_id = str(header["project_id"]) if header["project_id"] else None

if not project_id:
    st.stop()

project = app.get_project(user_id, project_id)

query = st.text_input("Search query", placeholder="Type a semantic query...")

result_k = 5

with st.expander("Metadata filters (optional)", expanded=False):
    use_filters = st.toggle("Apply metadata filters", value=False)
    doc_names = app.list_project_documents(user_id, project_id)
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
        fetch_k = vector_search_fetch_k(base_k=result_k, filters=filters)
        with st.spinner("Searching summaries..."):
            docs = app.vectorstore_service.similarity_search(project, query, k=fetch_k)
        if filters is not None:
            docs = filter_summary_documents_by_filters(docs, filters)[:result_k]

        if not docs:
            st.info("No summaries found.")
            st.stop()

        st.metric("Retrieved summaries", len(docs))
        st.markdown("### Retrieved summaries from FAISS")

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
    except Exception as exc:
        st.error(get_user_error_message(exc, f"Unexpected error while searching: {exc}"))
