"""
Gold QA dataset tab: generate entries, add manually, and light review scaffolding.
"""

from __future__ import annotations

from typing import Any, cast

import streamlit as st

from components.shared.evaluation_csv_utils import parse_evaluation_csv_list
from components.shared.metric_help import render_metric_with_help
from components.shared.request_runner import (
    is_request_running,
    render_result_payload,
    run_request_action,
)
from services.api_client import BackendClient
from services.ui_errors import (
    DocStoreError,
    LLMServiceError,
    get_user_error_message,
)


def _render_dataset_generation_result(payload: dict[str, Any]) -> None:
    created_entries = payload["created_entries"]
    skipped_duplicates = payload["skipped_duplicates"]
    deleted_existing_entries = payload["deleted_existing_entries"]
    mode = payload["generation_mode"]

    if mode == "replace":
        st.success(
            f"Dataset replaced successfully: {deleted_existing_entries} existing entr"
            f"{'y' if deleted_existing_entries == 1 else 'ies'} removed and "
            f"{len(created_entries)} new entr{'y' if len(created_entries) == 1 else 'ies'} created."
        )
    elif mode == "append_dedup":
        st.success(
            f"{len(created_entries)} entr{'y' if len(created_entries) == 1 else 'ies'} created. "
            f"{len(skipped_duplicates)} duplicate question"
            f"{'' if len(skipped_duplicates) == 1 else 's'} skipped."
        )
    else:
        st.success(
            f"{len(created_entries)} QA dataset entr{'y' if len(created_entries) == 1 else 'ies'} created."
        )

    if skipped_duplicates:
        st.markdown("#### Skipped duplicate questions")
        for question in skipped_duplicates:
            st.markdown(f"- {question}")

    if created_entries:
        st.markdown("#### Created entries")
        for entry in created_entries:
            with st.expander(f"#{entry.id} — {entry.question}", expanded=False):
                if entry.expected_answer:
                    st.markdown("**Expected answer**")
                    st.write(entry.expected_answer)

                if entry.expected_doc_ids:
                    st.markdown("**Expected doc_ids**")
                    st.code("\n".join(entry.expected_doc_ids), language="text")

                if entry.expected_sources:
                    st.markdown("**Expected source files**")
                    st.code("\n".join(entry.expected_sources), language="text")


def render_evaluation_gold_qa_tab(payload: dict[str, Any]) -> None:
    backend_client = cast(BackendClient, payload["backend_client"])
    user_id = str(payload["user_id"])
    project_id = str(payload["project_id"])
    wk = str(payload["widget_key_suffix"])
    project_documents = cast(list[str], payload["project_documents"])
    dataset_generation_request_key = str(payload["dataset_generation_request_key"])
    dataset_generation_result_key = str(payload["dataset_generation_result_key"])
    entry_count = int(payload["entry_count"])

    st.caption(
        "Build and evolve the gold QA dataset: generate from indexed assets, add rows by hand, "
        "then use **Dataset evaluation → Entries** to inspect or remove rows at scale."
    )

    tab_generate, tab_add, tab_review = st.tabs(["Generate", "Add manually", "Review"])

    with tab_generate:
        st.markdown("##### Generate entries automatically")
        st.caption("LLM-authored questions and optional gold fields from your project documents.")

        generation_col1, generation_col2 = st.columns(2)
        with generation_col1:
            generation_num_questions = st.number_input(
                "Number of questions to generate",
                min_value=1,
                max_value=20,
                value=5,
                step=1,
                key=f"eval_gold_numq_{wk}",
            )
        with generation_col2:
            generation_selected_files = st.multiselect(
                "Restrict generation to selected source files (optional)",
                options=project_documents,
                default=[],
                help="Leave empty to use all project documents.",
                key=f"eval_gold_source_files_{wk}",
            )

        generation_mode = st.radio(
            "Generation mode",
            options=["append", "replace", "append_dedup"],
            format_func=lambda mode: {
                "append": "Append",
                "replace": "Replace dataset",
                "append_dedup": "Append with dedup",
            }[mode],
            horizontal=True,
            help=(
                "Append: keep existing entries and add new ones. "
                "Replace dataset: delete all existing entries before inserting new ones. "
                "Append with dedup: keep existing entries and skip generated questions already present."
            ),
            key=f"eval_gold_gen_mode_{wk}",
        )

        def _run_dataset_generation():
            return backend_client.generate_qa_dataset_entries(
                user_id=user_id,
                project_id=project_id,
                num_questions=int(generation_num_questions),
                source_files=generation_selected_files or None,
                generation_mode=generation_mode,
            )

        def _map_dataset_generation_error(exc: Exception) -> str:
            if isinstance(exc, DocStoreError):
                return get_user_error_message(
                    exc, "Unable to inspect indexed assets while generating QA entries."
                )
            if isinstance(exc, LLMServiceError):
                return get_user_error_message(
                    exc, "The language model failed while generating QA dataset entries."
                )
            return get_user_error_message(
                exc, f"Unexpected error while generating QA dataset entries: {exc}"
            )

        generate_clicked = st.button(
            "Generate QA dataset entries",
            use_container_width=True,
            disabled=is_request_running(dataset_generation_request_key),
            key=f"eval_gold_generate_{wk}",
        )

        if generate_clicked and not project_documents:
            st.warning("Please ingest documents before generating QA dataset entries.")
        else:
            run_request_action(
                request_key=dataset_generation_request_key,
                result_key=dataset_generation_result_key,
                trigger=generate_clicked,
                can_run=bool(project_documents),
                action=_run_dataset_generation,
                spinner_text="Generating QA dataset entries from project assets...",
                error_mapper=_map_dataset_generation_error,
            )

        render_result_payload(
            result_key=dataset_generation_result_key,
            on_success=_render_dataset_generation_result,
        )

    with tab_add:
        st.markdown("##### Add an entry manually")
        st.caption("Capture a question and optional gold answer, doc IDs, and source filenames.")

        with st.form(f"qa_dataset_create_form_{wk}", clear_on_submit=True):
            dataset_question = st.text_area(
                "Dataset question",
                placeholder="e.g. What is the main objective of the report?",
                height=110,
            )
            dataset_expected_answer = st.text_area(
                "Expected answer (optional)",
                placeholder="Reference answer used later for evaluation and LLM-as-a-judge scoring.",
                height=120,
            )
            col1, col2 = st.columns(2)
            with col1:
                dataset_expected_doc_ids = st.text_input(
                    "Expected doc_ids (optional, comma-separated)",
                    placeholder="doc_1, doc_2",
                )
            with col2:
                dataset_expected_sources = st.text_input(
                    "Expected source files (optional, comma-separated)",
                    placeholder="report.pdf, appendix.pdf",
                )
            add_entry_clicked = st.form_submit_button(
                "Add QA entry",
                use_container_width=True,
            )

        if add_entry_clicked:
            try:
                entry = backend_client.create_qa_dataset_entry(
                    user_id=user_id,
                    project_id=project_id,
                    question=dataset_question,
                    expected_answer=dataset_expected_answer or None,
                    expected_doc_ids=parse_evaluation_csv_list(dataset_expected_doc_ids),
                    expected_sources=parse_evaluation_csv_list(dataset_expected_sources),
                )
                st.session_state["qa_dataset_success_message"] = (
                    f"QA entry #{entry.id} added to project dataset."
                )
                st.rerun()
            except Exception as exc:
                st.session_state["qa_dataset_error_message"] = get_user_error_message(
                    exc,
                    f"Unable to add QA dataset entry: {exc}",
                )
                st.rerun()

    with tab_review:
        st.markdown("##### Review")
        st.caption(
            "Lightweight status for the dataset. Detailed listing, benchmark scores, and delete actions "
            "live under **Dataset evaluation → Entries** so there is a single entries surface."
        )
        render_metric_with_help(
            label="Entries in this project",
            value=entry_count,
            metric_key="gold_qa_entry_count",
        )
        st.markdown("###### Hygiene tips")
        st.markdown(
            "- Use **Generate → Append with dedup** to grow the dataset without repeating questions.\n"
            "- Prefer **Dataset evaluation → Entries** when you need to audit wording, gold fields, or remove a row.\n"
            "- After substantive edits, re-run **Dataset evaluation** (Overview tab) to refresh aggregates."
        )
