import json

import streamlit as st

from typing import cast
from src.app.ragcraft_app import RAGCraftApp
from src.domain.retrieval_filters import RetrievalFilters
from src.auth.guards import require_authentication
from src.core.error_utils import get_user_error_message
from src.core.exceptions import DocStoreError, LLMServiceError, VectorStoreError
from src.ui.confidence_display import format_confidence_with_band
from src.ui.layout import apply_layout
from src.ui.page_header import render_page_header
from src.ui.request_runner import (
    is_request_running,
    run_request_action,
    render_result_payload,
)


st.set_page_config(
    page_title="Retrieval Inspector | RAGCraft",
    page_icon="🧠",
    layout="wide",
)

require_authentication("pages/retrieval_inspector.py")
apply_layout()

INSPECT_REQUEST_KEY = "retrieval_inspector_request_running"
INSPECT_RESULT_KEY = "retrieval_inspector_result_payload"


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
        retrieval_mode = metadata.get("retrieval_mode")
        retrieval_score = metadata.get("retrieval_score")

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

        if retrieval_mode:
            badges.append(f"mode {retrieval_mode}")

        if retrieval_score is not None:
            badges.append(f"score {float(retrieval_score):.4f}")

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
    subtitle="Understand what is retrieved, rewritten, merged, reranked and injected into the final prompt.",
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

st.markdown("### Retrieval options")
opt_col_1, opt_col_2 = st.columns(2)

with opt_col_1:
    enable_query_rewrite = st.toggle(
        "Enable query rewrite",
        value=True,
        help="Rewrite the user query into a retrieval-optimized search query before recall.",
    )

with opt_col_2:
    use_adaptive_retrieval = st.toggle(
        "Adaptive retrieval (intent-based k and hybrid)",
        value=True,
        help="When on, similarity k and hybrid follow query intent; turn off to force hybrid manually.",
    )

enable_hybrid_retrieval_override: bool | None = None
if not use_adaptive_retrieval:
    enable_hybrid_retrieval_override = st.toggle(
        "Enable hybrid retrieval (FAISS + BM25)",
        value=True,
        help="Combine semantic retrieval from FAISS with lexical retrieval from BM25.",
    )
else:
    st.caption("Hybrid and top‑k are chosen per query intent unless adaptive is off.")

chat_history_mode = st.toggle("Include current chat history context", value=False)

chat_history = []
if chat_history_mode:
    chat_history = app.chat_service.get_messages()
    chat_history = [f"{msg['role']}: {msg['content']}" for msg in chat_history[-6:]]

with st.expander("Advanced metadata filters (optional)", expanded=False):
    use_metadata_filters = st.toggle(
        "Restrict retrieval by metadata",
        value=False,
        help="Narrows FAISS over-fetch and BM25 corpus to matching assets. Main chat is unchanged.",
    )
    project_doc_names = app.list_project_documents(user_id, project_id)
    filter_sources = st.multiselect(
        "Source files",
        options=project_doc_names,
        default=[],
        help="When set, only chunks from these uploaded files are eligible for retrieval.",
    )
    filter_content_types = st.multiselect(
        "Content types",
        options=["text", "table", "image"],
        default=[],
    )
    fcol_a, fcol_b = st.columns(2)
    with fcol_a:
        filter_page_start = st.number_input(
            "Page range start (0 = ignore)",
            min_value=0,
            value=0,
            step=1,
        )
    with fcol_b:
        filter_page_end = st.number_input(
            "Page range end (0 = ignore)",
            min_value=0,
            value=0,
            step=1,
        )


def _optional_retrieval_filters() -> RetrievalFilters | None:
    if not use_metadata_filters:
        return None
    ps = int(filter_page_start) if int(filter_page_start) > 0 else None
    pe = int(filter_page_end) if int(filter_page_end) > 0 else None
    if (ps is None) != (pe is None):
        st.warning("Set both page start and end, or leave both at 0, to filter by page range.")
        ps, pe = None, None
    elif ps is not None and pe is not None and ps > pe:
        st.warning("Page range start cannot be greater than end.")
        ps, pe = None, None
    f = RetrievalFilters(
        source_files=list(filter_sources),
        content_types=list(filter_content_types),
        page_start=ps,
        page_end=pe,
    )
    if f.is_empty():
        return None
    return f


def _run_inspection():
    return app.inspect_retrieval(
        user_id=user_id,
        project_id=project_id,
        question=question,
        chat_history=chat_history,
        enable_query_rewrite_override=enable_query_rewrite,
        enable_hybrid_retrieval_override=enable_hybrid_retrieval_override,
        filters=_optional_retrieval_filters(),
    )


def _map_inspection_error(exc: Exception) -> str:
    if isinstance(exc, VectorStoreError):
        return get_user_error_message(exc, "Unable to query the FAISS index for this inspection.")
    if isinstance(exc, DocStoreError):
        return get_user_error_message(exc, "Unable to reload retrieved assets from SQLite.")
    if isinstance(exc, LLMServiceError):
        return get_user_error_message(exc, "The language model failed while preparing the final prompt or answer.")
    return get_user_error_message(exc, f"Unexpected error while inspecting retrieval: {exc}")


def _render_pipeline_latency(latency: dict | None):
    if not latency:
        return

    st.markdown("### Pipeline latency (ms)")
    st.caption(
        "Retrieval-side stages through prompt build; total is wall time for this inspection run "
        "(answer generation is not executed here)."
    )
    cols = st.columns(6)
    labels = [
        ("Query rewrite", "query_rewrite_ms"),
        ("Retrieval", "retrieval_ms"),
        ("Reranking", "reranking_ms"),
        ("Prompt build", "prompt_build_ms"),
        ("Answer gen.", "answer_generation_ms"),
        ("Total", "total_ms"),
    ]
    for col, (label, key) in zip(cols, labels):
        with col:
            val = latency.get(key)
            try:
                num = float(val) if val is not None else 0.0
            except (TypeError, ValueError):
                num = 0.0
            st.metric(label, f"{num:.2f}")


def _render_inspection_result(pipeline):
    if pipeline is None:
        st.warning("No retrieval result available for this query.")
        return

    rs = pipeline.get("retrieval_strategy") or {}
    strat_k = rs.get("k")
    strat_hybrid = rs.get("use_hybrid")
    strat_filters = rs.get("apply_filters")
    filters_active = pipeline.get("retrieval_filters") is not None

    top_metrics = st.columns(4)
    with top_metrics[0]:
        st.metric("Mode", pipeline["retrieval_mode"])
    with top_metrics[1]:
        st.metric("Rewrite", "On" if pipeline["query_rewrite_enabled"] else "Off")
    with top_metrics[2]:
        st.metric("Hybrid", "On" if pipeline["hybrid_retrieval_enabled"] else "Off")
    with top_metrics[3]:
        st.metric("Intent", str(pipeline.get("query_intent", "unknown")))

    strat_cols = st.columns(5)
    with strat_cols[0]:
        st.metric("Strategy k", strat_k if strat_k is not None else "—")
    with strat_cols[1]:
        st.metric(
            "Strategy hybrid",
            "On" if strat_hybrid is True else ("Off" if strat_hybrid is False else "—"),
        )
    with strat_cols[2]:
        st.metric(
            "Strategy filters",
            "On" if strat_filters is True else ("Off" if strat_filters is False else "—"),
        )
    with strat_cols[3]:
        st.metric("Filters active", "Yes" if filters_active else "No")
    with strat_cols[4]:
        st.metric(
            "Adaptive",
            "On" if pipeline.get("adaptive_retrieval_enabled") else "Off",
        )

    recall_cols = st.columns(4)
    with recall_cols[0]:
        st.metric("FAISS recall", len(pipeline["vector_summary_docs"]))
    with recall_cols[1]:
        st.metric("BM25 recall", len(pipeline["bm25_summary_docs"]))
    with recall_cols[2]:
        prompt_assets = pipeline.get("prompt_context_assets") or pipeline.get("reranked_raw_assets") or []
        st.metric("Prompt assets", len(prompt_assets))
    with recall_cols[3]:
        st.metric(
            "Confidence",
            format_confidence_with_band(float(pipeline["confidence"])),
        )

    _render_pipeline_latency(pipeline.get("latency"))

    cc = pipeline.get("context_compression") or {}
    if cc.get("enabled") is not None:
        st.markdown("### Context compression (prompt-facing chars)")
        c1, c2, c3, c4 = st.columns(4)
        with c1:
            st.metric("Before", cc.get("chars_before", "—"))
        with c2:
            st.metric("After", cc.get("chars_after", "—"))
        with c3:
            r = cc.get("ratio")
            st.metric("Ratio (after/before)", f"{float(r):.3f}" if r is not None else "—")
        with c4:
            st.metric(
                "Applied",
                "Yes" if cc.get("applied") else "No",
            )

    with st.expander("1. Original query and rewritten retrieval query", expanded=True):
        st.markdown("**Original user query**")
        st.write(pipeline["question"])

        st.markdown("**Rewritten retrieval query**")
        st.write(pipeline["rewritten_question"])

        if pipeline["rewritten_question"].strip() == pipeline["question"].strip():
            st.caption("The rewrite stage kept the query unchanged or almost unchanged.")

    with st.expander("2. FAISS summaries retrieved from vector search", expanded=True):
        _render_summary_docs(pipeline["vector_summary_docs"])

    with st.expander("3. BM25 summaries retrieved from lexical search", expanded=False):
        _render_summary_docs(pipeline["bm25_summary_docs"])

    with st.expander("4. Merged summaries retained after hybrid recall", expanded=True):
        _render_summary_docs(pipeline["recalled_summary_docs"])

    with st.expander("5. Doc IDs retained after merged recall", expanded=False):
        _render_doc_ids(
            pipeline["recalled_doc_ids"],
            empty_message="No doc_ids were retained from the recall stage.",
        )

    with st.expander("6. Raw assets reloaded from SQLite", expanded=False):
        st.caption(
            "For text assets chunked with by_title, each expander shows both the final chunk "
            "and the original extracted text elements grouped into it."
        )
        _render_raw_assets(
            pipeline["recalled_raw_assets"],
            title_prefix="Raw asset",
        )

    with st.expander("7. Final assets injected into the prompt", expanded=True):
        _render_doc_ids(
            pipeline["selected_doc_ids"],
            empty_message="No doc_ids were retained after reranking.",
        )

        st.markdown("### Source references")
        _render_source_references(pipeline["source_references"])

        st.markdown("### Final prompt assets (after contextual compression)")
        st.caption(
            "Reranked assets are compressed for the LLM when enabled; full reranked payloads "
            "remain available under structured payload / recalled assets above."
        )
        _render_raw_assets(
            pipeline.get("prompt_context_assets") or pipeline.get("reranked_raw_assets") or [],
            title_prefix="Prompt asset",
        )

    with st.expander("8. Raw context injected into the prompt", expanded=False):
        st.code(pipeline["raw_context"], language="text")

    with st.expander("9. Final prompt generated", expanded=False):
        st.code(pipeline["prompt"], language="text")

    with st.expander("10. Structured pipeline payload", expanded=False):
        debug_payload = {
            "question": pipeline["question"],
            "rewritten_question": pipeline["rewritten_question"],
            "query_intent": pipeline.get("query_intent"),
            "chat_history": pipeline["chat_history"],
            "retrieval_mode": pipeline["retrieval_mode"],
            "query_rewrite_enabled": pipeline["query_rewrite_enabled"],
            "hybrid_retrieval_enabled": pipeline["hybrid_retrieval_enabled"],
            "adaptive_retrieval_enabled": pipeline.get("adaptive_retrieval_enabled"),
            "retrieval_strategy": pipeline.get("retrieval_strategy"),
            "retrieval_filters": pipeline.get("retrieval_filters"),
            "recalled_doc_ids": pipeline["recalled_doc_ids"],
            "selected_doc_ids": pipeline["selected_doc_ids"],
            "confidence": pipeline["confidence"],
            "source_references": pipeline["source_references"],
            "latency_ms": pipeline.get("latency_ms"),
            "latency": pipeline.get("latency"),
            "context_compression": pipeline.get("context_compression"),
            "prompt_context_assets_doc_ids": [
                a.get("doc_id")
                for a in (pipeline.get("prompt_context_assets") or [])
                if isinstance(a, dict)
            ],
        }

        st.code(json.dumps(debug_payload, indent=2, ensure_ascii=False), language="json")


run_clicked = st.button(
    "Inspect retrieval pipeline",
    use_container_width=True,
    disabled=is_request_running(INSPECT_REQUEST_KEY),
)

if run_clicked and not question.strip():
    st.warning("Please enter a query.")
else:
    run_request_action(
        request_key=INSPECT_REQUEST_KEY,
        result_key=INSPECT_RESULT_KEY,
        trigger=run_clicked,
        can_run=bool(question.strip()),
        action=_run_inspection,
        spinner_text="Inspecting retrieval pipeline...",
        error_mapper=_map_inspection_error,
    )

render_result_payload(
    result_key=INSPECT_RESULT_KEY,
    on_success=_render_inspection_result,
)
