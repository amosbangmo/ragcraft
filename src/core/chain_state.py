import streamlit as st


CHAIN_CACHE_KEY = "rag_chain_cache"


def _ensure_chain_cache():
    if CHAIN_CACHE_KEY not in st.session_state:
        st.session_state[CHAIN_CACHE_KEY] = {}


def get_cached_chain(project_key: str):
    """
    Return the cached RAG chain for a given project key.
    """
    _ensure_chain_cache()
    return st.session_state[CHAIN_CACHE_KEY].get(project_key)


def set_cached_chain(project_key: str, chain):
    """
    Store a RAG chain in the session cache for a given project key.
    """
    _ensure_chain_cache()
    st.session_state[CHAIN_CACHE_KEY][project_key] = chain


def invalidate_project_chain(project_key: str):
    """
    Remove the cached chain for a specific project.
    """
    _ensure_chain_cache()
    st.session_state[CHAIN_CACHE_KEY].pop(project_key, None)


def invalidate_all_project_chains():
    """
    Clear the full chain cache for the current Streamlit session.
    """
    if CHAIN_CACHE_KEY in st.session_state:
        st.session_state[CHAIN_CACHE_KEY] = {}
