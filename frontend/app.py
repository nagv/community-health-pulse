"""Streamlit entry point. Start from frontend/ (so .streamlit/config.toml applies) or use start-frontend.ps1."""

import json
import sys
from pathlib import Path

import streamlit as st

# `streamlit run` puts frontend/ (the script's folder) on sys.path, not the repository root.
ROOT = str(Path(__file__).resolve().parents[1])
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from frontend import client, state
from frontend.components import filters as filter_form
from frontend.components import sidebar
from frontend.theme import CSS
from frontend.views import chat, explore, overview

TITLES = {
    "Overview": ("Clinic activity overview", "Understand recorded visits across your clinics"),
    "Explore Data": ("Explore recorded visits", "Understand recorded visits across your clinics"),
    "Ask the Data": ("Ask your clinic data", "Answers grounded in your uploaded dataset"),
}
EMPTY_STATES = {
    "Overview": (
        "Your clinic dashboard",
        "Visit totals, weekly trends, condition breakdowns and locality comparisons will appear here.",
    ),
    "Explore Data": (
        "Explore your visit records",
        "Filter your dataset, inspect condition counts and browse individual recorded visits here.",
    ),
    "Ask the Data": (
        "Ask questions with evidence",
        "Ask about counts, trends and comparisons. Answers, charts and completed analysis steps will appear here.",
    ),
}

st.set_page_config(
    page_title="Community Health Pulse", page_icon="🩺", layout="wide", initial_sidebar_state="auto"
)
st.markdown(CSS, unsafe_allow_html=True)
state.init()
sidebar.render()

header = st.empty()
selection_summary = st.empty()
with st.container(key="workspace-nav"):
    view = st.radio("Workspace", state.VIEWS, key=state.VIEW, horizontal=True, label_visibility="collapsed")
with header.container():
    title, caption = TITLES[view]
    st.title(title)
    st.caption(caption)

try:
    health = client.health()
except client.ApiError as exc:
    st.error(str(exc))
    st.info("Start the backend on port 8000, then refresh this page.")
    st.stop()


def empty_state() -> None:
    st.info("Upload a CSV in the sidebar or select **Load demo dataset** to open this section.")
    with st.container(border=True):
        heading, description = EMPTY_STATES[view]
        st.subheader(heading)
        st.write(description)
        st.code("visit_id,visit_date,locality,age,gender,condition", language=None)
        st.caption("Dates: YYYY-MM-DD · Age: whole years, 0–120 · One row per visit")
    for col, (heading, body) in zip(
        st.columns(3),
        [
            ("Explore patterns", "Filter visits and compare groups."),
            ("Ask your data", "Get answers through approved analysis tools."),
            ("Follow the evidence", "Inspect the calculations and filters behind each answer."),
        ],
    ):
        with col, st.container(border=True):
            st.subheader(heading)
            st.write(body)


info = st.session_state[state.DATASET]
if not info:
    empty_state()
    st.stop()

st.markdown(
    '<span class="pill">' + ("Synthetic demo data" if info["synthetic"] else "Uploaded CSV") + "</span>",
    unsafe_allow_html=True,
)
filters = filter_form.render(info)
sidebar.footer()

signature = json.dumps(filters, sort_keys=True)
if signature != st.session_state[state.FILTER_SIGNATURE]:
    st.session_state[state.PAGE] = 1
    st.session_state[state.FILTER_SIGNATURE] = signature

try:
    with st.spinner("Calculating clinic activity…"):
        if view == "Ask the Data":
            data, summary = None, client.summary(info["dataset_id"], filters)
        else:
            data = client.dashboard(info["dataset_id"], filters, st.session_state[state.PAGE])
            summary = data["summary"]
except client.ApiError as exc:
    st.error(str(exc))
    st.stop()
selection_summary.info(filter_form.summary_line(filters, summary["recorded_visits"]))

if view == "Overview":
    overview.render(data)
elif view == "Explore Data":
    explore.render(data)
else:
    chat.render(info, filters, health["agent_configured"])
