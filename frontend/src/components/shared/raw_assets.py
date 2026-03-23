import base64
from typing import Literal

import streamlit as st

TitleMode = Literal["chat", "evaluation"]


def _render_html_table(table_html: str):
    st.markdown(table_html, unsafe_allow_html=True)


def _render_base64_image(base64_content: str, title: str | None = None):
    try:
        image_bytes = base64.b64decode(base64_content)
        if title:
            st.markdown(f"**{title}**")
        st.image(image_bytes)
    except Exception:
        st.warning("Unable to render image asset.")


def _build_asset_title(asset: dict, index: int, mode: TitleMode) -> str:
    source_file = asset.get("source_file", "unknown")
    content_type = asset.get("content_type", "unknown")
    metadata = asset.get("metadata", {}) or {}

    table_title = metadata.get("table_title")
    image_title = metadata.get("image_title")
    page_number = metadata.get("page_number")
    page_start = metadata.get("page_start")
    page_end = metadata.get("page_end")
    start_element_index = metadata.get("start_element_index")
    end_element_index = metadata.get("end_element_index")

    if mode == "evaluation":
        title_parts = [f"Source {index} — {source_file}"]
    else:
        title_parts = [f"[{index}] {source_file}"]

    if content_type == "table" and table_title:
        title_parts.append(f"— {table_title}")
    elif content_type == "image" and image_title:
        title_parts.append(f"— {image_title}")

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

    return " ".join(title_parts)


def render_raw_assets(
    raw_assets: list[dict],
    *,
    heading: str | None = None,
    mode: TitleMode = "chat",
):
    if not raw_assets:
        return

    if heading:
        st.markdown(heading)

    for index, asset in enumerate(raw_assets, start=1):
        content_type = asset.get("content_type", "unknown")
        raw_content = asset.get("raw_content", "")
        metadata = asset.get("metadata", {}) or {}

        table_title = metadata.get("table_title")
        image_title = metadata.get("image_title")

        with st.expander(_build_asset_title(asset, index, mode)):
            if content_type == "text":
                st.write(raw_content)
                continue

            if content_type == "table":
                if table_title:
                    st.markdown(f"**{table_title}**")

                if raw_content:
                    _render_html_table(raw_content)
                else:
                    st.caption("Empty table payload.")
                continue

            if content_type == "image":
                _render_base64_image(raw_content, title=image_title)
                continue

            st.write(raw_content)
