import streamlit as st
from components.shared.layout import apply_layout
from utils.guards import require_authentication

st.set_page_config(
    page_title="RAGCraft",
    page_icon="🚀",
    layout="wide",
    initial_sidebar_state="expanded",
)

require_authentication("streamlit_app.py")
apply_layout()


st.markdown(
    """
    <div class="hero-card">
        <div class="hero-badge">RAGCraft</div>
        <h1 class="hero-title">Build, search and chat with your document knowledge bases</h1>
        <p class="hero-subtitle">
            Multi-project Retrieval-Augmented Generation system with ingestion, vector search,
            evaluation and conversational QA.
        </p>
    </div>
    """,
    unsafe_allow_html=True,
)

st.info("Use the sidebar to navigate between Projects, Ingestion, Chat, Search and Evaluation.")
