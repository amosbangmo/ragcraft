"""
Streamlit ``session_state`` cache for per-browser vector-chain handles (UI process only).

Imports ``streamlit``. FastAPI uses :class:`~src.infrastructure.caching.process_project_chain_cache.ProcessProjectChainCache` instead.
"""

from __future__ import annotations

import streamlit as st

CHAIN_CACHE_KEY = "rag_chain_cache"


def _ensure_chain_cache() -> None:
    if CHAIN_CACHE_KEY not in st.session_state:
        st.session_state[CHAIN_CACHE_KEY] = {}


def get_cached_chain(project_key: str):
    """Return the cached RAG chain (vector-store handle) for a project key, if any."""
    _ensure_chain_cache()
    return st.session_state[CHAIN_CACHE_KEY].get(project_key)


def set_cached_chain(project_key: str, chain) -> None:
    """Store a RAG chain in the Streamlit session cache for a project key."""
    _ensure_chain_cache()
    st.session_state[CHAIN_CACHE_KEY][project_key] = chain


def invalidate_project_chain_session(project_key: str) -> None:
    """Remove the cached chain for a specific project from the current Streamlit session."""
    _ensure_chain_cache()
    st.session_state[CHAIN_CACHE_KEY].pop(project_key, None)


def invalidate_all_project_chains_session() -> None:
    """Clear the full chain cache for the current Streamlit session."""
    if CHAIN_CACHE_KEY in st.session_state:
        st.session_state[CHAIN_CACHE_KEY] = {}


# Backward-compatible aliases for modules that imported the old session helpers by these names.
invalidate_project_chain = invalidate_project_chain_session
invalidate_all_project_chains = invalidate_all_project_chains_session
