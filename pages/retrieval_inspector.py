import json

import streamlit as st

from typing import cast
from src.app.ragcraft_app import RAGCraftApp
from src.auth.guards import require_authentication
from src.core.exceptions import DocStoreError, LLMServiceError, VectorStoreError
from src.ui.layout import apply_layout
from src.ui.page_header import render_page_header


st.set_page_config(
    page_title="Retrieval Inspector | RAGCraft",
    page_icon="🧠",
    layout="wide",
)

require_authentication("pages/retrieval_inspector.py")
apply_layout()


def _get_user_error_message(exc: Exception, default_message: str) -> str:
    return getattr(exc, "user_message", default_message)


def _render_summary_docs(docs: list):
    if not docs:
        st.info("No summaries available.")
        return

    st.metric("Retrieved summaries", len(docs))

    for index, doc in enumerate(docs, start=1):
        metadata = doc.metadata or {}
        source_file = metadata.get("source_file", metadata.get("file_name", "unknown"))
        content_type = metadata.get("content_type", "unknown")
        doc_id = metadata.get("doc_id", "?")

        badges = []
        if metadata.get("page_number") is not None:
            badges.append(f"page {metadata.get('page_number')}")
        elif metadata.get("page_start") is not None and metadata.get("page_end") is not None:
            start_page = metadata.get("page_start")
            end_page = metadata.get("page_end")
            if start_page == end_page:
                badges.append(f"page {start_page}")
            else:
                badges.append(f"pages {start_page}-{end_page}")

        st.markdown(
            f"""
            <div class="source-card">
                <div class="source-title">#{index} — {source_file} — {content_type} — doc_id {doc_id}</div>
                <div class="source-preview">{doc.page_content}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        if badges:
            st.caption(" • ".join(badges))


def _render_doc_ids(doc_ids: list[str], empty_message: str):
    if not doc_ids:
        st.info(empty_message)
        return

    st.metric("Doc IDs", len(doc_ids))
    st.code("\n".join(doc_ids), language="text")


def _render_text_chunk_lineage(asset: dict):
    metadata = asset.get("metadata", {}) or {}
    chunking_strategy = metadata.get("chunking_strategy")
    orig_element_count = metadata.get("orig_element_count", 0)
    chunk_char_count = metadata.get("chunk_char_count", 0)
    orig_total_text_chars = metadata.get("orig_total_text_chars", 0)
    chunk_title = metadata.get("chunk_title")
    orig_categories = metadata.get("orig_element_categories", []) or []
    orig_previews = metadata.get("orig_elements_preview", []) or []
    previews_truncated = metadata.get("orig_elements_preview_truncated", False)

    if chunking_strategy not in {"by_title", "none"}:
        return

    st.markdown("### Text chunk lineage")

    m1, m2, m3 = st.columns(3)
    with m1:
        st.metric("Chunking", chunking_strategy)
    with m2:
        st.metric("Original elements", orig_element_count)
    with m3:
        st.metric("Chunk chars", chunk_char_count)

    if orig_total_text_chars:
        st.caption(f"Original combined text chars: {orig_total_text_chars}")

    if chunk_title:
        st.markdown(f"**Chunk title:** {chunk_title}")

    if orig_categories:
        st.markdown(f"**Original categories:** {', '.join(orig_categories)}")

    st.markdown("### Final chunk injected / stored")
    st.code((asset.get("raw_content", "") or "")[:4000], language="text")

    st.markdown("### Original extracted text elements before chunking")

    if not orig_previews:
        st.info("No original text element previews available for this chunk.")
        return

    for preview in orig_previews:
        element_index = preview.get("element_index")
        page_number = preview.get("page_number")
        category = preview.get("category", "unknown")
        text_preview = preview.get("text_preview", "")

        title_parts = [f"Element {element_index}" if element_index is not None else "Element ?"]
        title_parts.append(f"— {category}")
        if page_number is not None:
            title_parts.append(f"— page {page_number}")

        with st.expander(" ".join(title_parts)):
            st.code(text_preview or "[empty]", language="text")

    if previews_truncated:
        st.caption("Preview truncated: not all original text elements are shown.")


def _render_raw_asset_detail(asset: dict):
    metadata = asset.get("metadata", {}) or {}
    content_type = asset.get("content_type", "unknown")
    raw_content = asset.get("raw_content", "") or ""
    summary = asset.get("summary", "") or ""

    if summary:
        st.markdown("**Summary**")
        st.write(summary)

    st.markdown("**Metadata**")
    st.json(metadata)

    if content_type == "text":
        _render_text_chunk_lineage(asset)
        return

    st.markdown("**Raw preview**")
    if content_type == "table":
        st.markdown(raw_content[:3000], unsafe_allow_html=True)
    else:
        st.code(raw_content[:3000] if raw_content else "[empty]", language="text")


def _render_raw_assets(assets: list[dict], title_prefix: str):
    if not assets:
        st.info("No raw assets available.")
        return

    st.metric("Assets", len(assets))

    for index, asset in enumerate(assets, start=1):
        metadata = asset.get("metadata", {}) or {}
        source_file = asset.get("source_file", "unknown")
        content_type = asset.get("content_type", "unknown")
        doc_id = asset.get("doc_id", "?")
        rerank_score = metadata.get("rerank_score")

        title_parts = [f"{title_prefix} {index} — {source_file} — {content_type} — doc_id {doc_id}"]

        if metadata.get("table_title"):
            title_parts.append(f"— {metadata.get('table_title')}")
        if metadata.get("image_title"):
            title_parts.append(f"— {metadata.get('image_title')}")
        if metadata.get("chunk_title"):
            title_parts.append(f"— chunk {metadata.get('chunk_title')}")
        if metadata.get("page_number") is not None:
            title_parts.append(f"— page {metadata.get('page_number')}")
        elif metadata.get("page_start") is not None and metadata.get("page_end") is not None:
            start_page = metadata.get("page_start")
            end_page = metadata.get("page_end")
            if start_page == end_page:
                title_parts.append(f"— page {start_page}")
            else:
                title_parts.append(f"— pages {start_page}-{end_page}")
        if rerank_score is not None:
            title_parts.append(f"— rerank {float(rerank_score):.4f}")

        with st.expander(" ".join(title_parts)):
            _render_raw_asset_detail(asset)


def _render_source_references(source_references: list[dict]):
    if not source_references:
        st.info("No source references generated.")
        return

    for ref in source_references:
        label = ref.get("inline_label", "")
        display = ref.get("display_label", "")
        rerank_score = ref.get("rerank_score")

        if rerank_score is not None:
            st.markdown(f"- **{label}** — {display} — rerank `{float(rerank_score):.4f}`")
        else:
            st.markdown(f"- **{label}** — {display}")


header = render_page_header(
    badge="Retrieval Inspector",
    title="Inspect the RAG pipeline end to end",
    subtitle="Understand what is retrieved, reloaded, reranked and injected into the final prompt.",
    selector_label="Project for retrieval inspection",
)

app = cast(RAGCraftApp, header["app"])
user_id = str(header["user_id"])
project_id = str(header["project_id"]) if header["project_id"] else None

if not project_id:
    st.stop()

question = st.text_area(
    "User query",
    placeholder="Ask a question to inspect the retrieval pipeline...",
    height=120,
)

chat_history_mode = st.toggle("Include current chat history context", value=False)

chat_history = []
if chat_history_mode:
    chat_history = app.chat_service.get_messages()
    chat_history = [f"{msg['role']}: {msg['content']}" for msg in chat_history[-6:]]

run_clicked = st.button("Inspect retrieval pipeline", use_container_width=True)

if run_clicked and question:
    try:
        pipeline = app.inspect_retrieval(
            user_id=user_id,
            project_id=project_id,
            question=question,
            chat_history=chat_history,
        )

        if pipeline is None:
            st.warning("No retrieval result available for this query.")
            st.stop()

        top_metrics = st.columns(5)
        with top_metrics[0]:
            st.metric("Recall summaries", len(pipeline["recalled_summary_docs"]))
        with top_metrics[1]:
            st.metric("Recall doc_ids", len(pipeline["recalled_doc_ids"]))
        with top_metrics[2]:
            st.metric("Raw assets reloaded", len(pipeline["recalled_raw_assets"]))
        with top_metrics[3]:
            st.metric("Prompt assets", len(pipeline["reranked_raw_assets"]))
        with top_metrics[4]:
            st.metric("Confidence", pipeline["confidence"])

        with st.expander("1. User query", expanded=True):
            st.write(pipeline["question"])

        with st.expander("2. Summaries retrieved from FAISS", expanded=True):
            _render_summary_docs(pipeline["recalled_summary_docs"])

        with st.expander("3. Doc IDs retained after recall", expanded=False):
            _render_doc_ids(
                pipeline["recalled_doc_ids"],
                empty_message="No doc_ids were retained from the recall stage.",
            )

        with st.expander("4. Raw assets reloaded from SQLite", expanded=False):
            st.caption(
                "For text assets chunked with by_title, each expander now shows both the final chunk "
                "and the original extracted text elements that were grouped into it."
            )
            _render_raw_assets(
                pipeline["recalled_raw_assets"],
                title_prefix="Raw asset",
            )

        with st.expander("5. Final assets injected into the prompt", expanded=True):
            _render_doc_ids(
                pipeline["selected_doc_ids"],
                empty_message="No doc_ids were retained after reranking.",
            )
            st.markdown("### Source references")
            _render_source_references(pipeline["source_references"])
            st.markdown("### Final prompt assets")
            st.caption(
                "For text chunks, inspect the lineage section to compare the pre-chunk extracted elements "
                "with the final stored/injected chunk."
            )
            _render_raw_assets(
                pipeline["reranked_raw_assets"],
                title_prefix="Prompt asset",
            )

        with st.expander("6. Raw context injected into the prompt", expanded=False):
            st.code(pipeline["raw_context"], language="text")

        with st.expander("7. Final prompt generated", expanded=False):
            st.code(pipeline["prompt"], language="text")

        with st.expander("8. Structured pipeline payload", expanded=False):
            debug_payload = {
                "question": pipeline["question"],
                "chat_history": pipeline["chat_history"],
                "recalled_doc_ids": pipeline["recalled_doc_ids"],
                "selected_doc_ids": pipeline["selected_doc_ids"],
                "confidence": pipeline["confidence"],
                "source_references": pipeline["source_references"],
            }
            st.code(json.dumps(debug_payload, indent=2, ensure_ascii=False), language="json")

    except VectorStoreError as exc:
        st.error(_get_user_error_message(exc, "Unable to query the FAISS index for this inspection."))
    except DocStoreError as exc:
        st.error(_get_user_error_message(exc, "Unable to reload retrieved assets from SQLite."))
    except LLMServiceError as exc:
        st.error(_get_user_error_message(exc, "The language model failed while preparing the final prompt or answer."))
    except Exception as exc:
        st.error(_get_user_error_message(exc, f"Unexpected error while inspecting retrieval: {exc}"))
