"""Session-state keys and transitions shared by the frontend modules."""

import streamlit as st

DATASET = "dataset"
MESSAGES = "messages"
LAST_ANALYSIS = "last_analysis"
PAGE = "page"
FILTER_SIGNATURE = "filter_signature"
VIEW = "workspace_view"

VIEWS = ["Overview", "Explore Data", "Ask the Data"]
MAX_STORED_MESSAGES = 24
MAX_HISTORY_SENT = 12

_DEFAULTS = {DATASET: None, MESSAGES: [], LAST_ANALYSIS: None, PAGE: 1, FILTER_SIGNATURE: None}


def init() -> None:
    for key, value in _DEFAULTS.items():
        if key not in st.session_state:
            st.session_state[key] = value.copy() if isinstance(value, list) else value


def replace_dataset(info) -> None:
    """Switching datasets resets the conversation, paging and cached API results."""
    from frontend import client

    st.session_state[DATASET] = info
    clear_chat()
    st.session_state[PAGE] = 1
    st.session_state[FILTER_SIGNATURE] = None
    client.clear_caches()


def clear_chat() -> None:
    st.session_state[MESSAGES] = []
    st.session_state[LAST_ANALYSIS] = None
