"""Streamlit entry point. Start from frontend/ or use start-frontend.ps1."""

import hashlib
import json
import math
import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import streamlit as st

from frontend.charts import figure
from frontend.client import ApiError, api
from frontend.theme import CSS

st.set_page_config(
    page_title="Community Health Pulse", page_icon="🩺", layout="wide", initial_sidebar_state="auto"
)
st.markdown(CSS, unsafe_allow_html=True)

for key, value in {
    "dataset": None,
    "messages": [],
    "last_analysis": None,
    "page": 1,
    "filter_signature": None,
}.items():
    if key not in st.session_state:
        st.session_state[key] = value


def replace_dataset(info):
    st.session_state["dataset"] = info
    st.session_state["messages"] = []
    st.session_state["last_analysis"] = None
    st.session_state["page"] = 1
    st.session_state["filter_signature"] = None


with st.sidebar:
    st.markdown('<div class="brand"><span>⌁</span>Community<br>Health Pulse</div>', unsafe_allow_html=True)
    st.caption("YOUR DATASET")
    uploaded = st.file_uploader(
        "Upload clinic CSV", type=["csv"], help="UTF-8 CSV, up to 10 MB / 100,000 visits."
    )
    if st.button("Validate and load CSV", disabled=uploaded is None, use_container_width=True):
        try:
            with st.spinner("Validating your CSV…"):
                info = api(
                    "POST", "/datasets", files={"file": (uploaded.name, uploaded.getvalue(), "text/csv")}
                )
            replace_dataset(info)
            st.success("Dataset accepted.")
            st.rerun()
        except ApiError as exc:
            st.error(str(exc))
    if st.button("Load demo dataset", type="primary", use_container_width=True):
        try:
            with st.spinner("Loading synthetic visits…"):
                replace_dataset(api("POST", "/datasets/sample"))
            st.rerun()
        except ApiError as exc:
            st.error(str(exc))
    if st.session_state["dataset"]:
        info = st.session_state["dataset"]
        st.caption(info["name"])
        st.caption(f"{info['row_count']:,} accepted visits")
        st.markdown("**Synthetic demo data**" if info["synthetic"] else "**Uploaded dataset**")
        if st.button("Clear dataset", use_container_width=True):
            try:
                api("DELETE", f"/datasets/{info['dataset_id']}")
                replace_dataset(None)
                st.rerun()
            except ApiError as exc:
                st.error(str(exc))

header = st.empty()
selection_summary = st.empty()
with st.container(key="workspace-nav"):
    view = st.radio(
        "Workspace",
        ["Overview", "Explore Data", "Ask the Data"],
        key="workspace_view",
        horizontal=True,
        label_visibility="collapsed",
    )
title = {
    "Overview": "Clinic activity overview",
    "Explore Data": "Explore recorded visits",
    "Ask the Data": "Ask your clinic data",
}[view]
with header.container():
    st.title(title)
    st.caption(
        "Understand recorded visits across your clinics"
        if view != "Ask the Data"
        else "Answers grounded in your uploaded dataset"
    )

try:
    health = api("GET", "/health")
except ApiError as exc:
    st.error(str(exc))
    st.info("Start the backend on port 8000, then refresh this page.")
    st.stop()

info = st.session_state["dataset"]
if not info:
    st.sidebar.caption("Week 1 · Clinic analytics")
    st.info("Upload a CSV in the sidebar or select **Load demo dataset** to open this section.")
    with st.container(border=True):
        heading, description = {
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
        }[view]
        st.subheader(heading)
        st.write(description)
        st.code("visit_id,visit_date,locality,age,gender,condition", language=None)
        st.caption("Dates: YYYY-MM-DD · Age: whole years, 0–120 · One row per visit")
    cols = st.columns(3)
    for col, title, body in zip(
        cols,
        ["Explore patterns", "Ask your data", "Follow the evidence"],
        [
            "Filter visits and compare groups.",
            "Get answers through approved analysis tools.",
            "Inspect the calculations and filters behind each answer.",
        ],
    ):
        with col, st.container(border=True):
            st.subheader(title)
            st.write(body)
    st.stop()

st.markdown(
    '<span class="pill">' + ("Synthetic demo data" if info["synthetic"] else "Uploaded CSV") + "</span>",
    unsafe_allow_html=True,
)
with st.sidebar, st.container(key="filters"):
    st.subheader("Filters")
    suffix = info["dataset_id"]
    selected_dates = st.date_input(
        "Date range",
        value=(date.fromisoformat(info["start_date"]), date.fromisoformat(info["end_date"])),
        key="dates_" + suffix,
    )
    localities = st.multiselect(
        "Locality", info["localities"], placeholder="All localities", key="localities_" + suffix
    )
    ages = st.multiselect("Age band", info["age_bands"], placeholder="All ages", key="ages_" + suffix)
    conditions = st.multiselect(
        "Condition", info["conditions"], placeholder="All conditions", key="conditions_" + suffix
    )
    with st.expander("Additional filters"):
        genders = st.multiselect(
            "Gender", info["genders"], placeholder="All genders", key="genders_" + suffix
        )
    st.divider()
    st.caption("Week 1 · Clinic analytics")
    st.caption("Counts reflect recorded visits, not population prevalence.")
if len(selected_dates) != 2:
    st.info("Select both the start and end date.")
    st.stop()
filters = {
    "start_date": selected_dates[0].isoformat(),
    "end_date": selected_dates[1].isoformat(),
    "localities": localities,
    "age_bands": ages,
    "conditions": conditions,
    "genders": genders,
}
signature = json.dumps(filters, sort_keys=True)
if signature != st.session_state["filter_signature"]:
    st.session_state["page"] = 1
    st.session_state["filter_signature"] = signature


def show_chart(spec, key):
    if spec.get("truncated"):
        st.caption(
            f"Showing the first {len(spec['rows'])} of {spec['total_groups']} groups. Totals include all matching visits."
        )
    chart = figure(spec)
    if chart is None:
        st.info("No visits match this selection.")
    else:
        # Give Streamlit the same height as Plotly's SVG and remount when the
        # figure changes, rather than retaining a previous client-side layout.
        revision = hashlib.sha256(chart.to_json().encode("utf-8")).hexdigest()[:16]
        st.plotly_chart(
            chart,
            width="stretch",
            height=int(chart.layout.height),
            theme=None,
            config={"responsive": True, "displayModeBar": False, "scrollZoom": False},
            key=f"{key}-{revision}",
        )


def scope_text(scope):
    labels = []
    for key, label in [
        ("start_date", "From"),
        ("end_date", "To"),
        ("localities", "Locality"),
        ("age_bands", "Age"),
        ("conditions", "Condition"),
        ("genders", "Gender"),
        ("previous_period", "Earlier period"),
        ("current_period", "Later period"),
    ]:
        value = scope.get(key)
        if value:
            labels.append(
                label + ": " + (", ".join(map(str, value)) if isinstance(value, list) else str(value))
            )
    return " · ".join(labels) or "All records"


try:
    with st.spinner("Calculating clinic activity…"):
        data = api(
            "POST",
            f"/datasets/{info['dataset_id']}/analysis",
            json={"filters": filters, "page": st.session_state["page"], "page_size": 25},
        )
except ApiError as exc:
    st.error(str(exc))
    st.stop()
selection_summary.info(
    f"**Showing:** {selected_dates[0]:%d %b %Y} – {selected_dates[1]:%d %b %Y}"
    f" · {', '.join(localities) or 'All localities'}"
    f" · {', '.join(ages) or 'All ages'}"
    f" · {', '.join(conditions) or 'All conditions'}"
    f" · {', '.join(genders) or 'All genders'}"
    f" · **{data['summary']['recorded_visits']:,} recorded visits**"
)

if view in ("Overview", "Explore Data"):
    summary = data["summary"]
    with st.container(key="metrics"):
        metrics = st.columns(4)
        for col, label, value in zip(
            metrics,
            ["Recorded visits", "Localities", "Accepted-row completeness", "Date coverage"],
            [
                f"{summary['recorded_visits']:,}",
                summary["localities"],
                f"{summary['completeness_pct']:.1f}%",
                f"{summary['date_coverage_days']} days",
            ],
        ):
            col.metric(label, value)
    st.caption(
        "Completeness is measured after validation. Invalid files are rejected; this is not a clinical-quality score."
    )
    if not summary["recorded_visits"]:
        st.info("No visits match these filters. Broaden the date range or clear a filter.")
    if view == "Overview":
        with st.container(key="overview-primary"):
            left, right = st.columns([1.6, 1])
            for col, spec, key in [
                (left, data["charts"][0], "trend"),
                (right, data["charts"][1], "conditions"),
            ]:
                with col, st.container(border=True):
                    st.subheader(spec["title"])
                    show_chart(spec, key)
        with st.container(key="overview-secondary"):
            left, right = st.columns([1.6, 1])
            with left, st.container(border=True):
                st.subheader("Visits by locality")
                show_chart(data["charts"][2], "localities")
            with right, st.container(border=True):
                st.subheader("Data quality")
                report = info["validation"]
                st.success("All accepted rows passed validation.")
                st.write(f"{report['duplicates_removed']:,} exact duplicates removed")
                st.caption(f"{report['input_rows']:,} input rows · {report['accepted_rows']:,} accepted rows")
                for warning in report["warnings"]:
                    st.warning(warning)
                st.caption("Visit counts can include repeat visits by the same person.")
        st.download_button(
            "Export analysis", json.dumps(data, indent=2), "clinic-analysis.json", "application/json"
        )
    else:
        with st.container(border=True):
            st.subheader("Condition breakdown")
            if data["condition_groups"] > len(data["conditions"]):
                st.caption(f"Showing the top 50 of {data['condition_groups']} recorded conditions.")
            st.dataframe(data["conditions"], use_container_width=True, hide_index=True)
        with st.container(border=True):
            st.subheader("Visit records")
            total = data["records"]["total"]
            pages = max(1, math.ceil(total / 25))
            st.number_input("Page", min_value=1, max_value=pages, key="page", step=1)
            st.caption(f"{total:,} matching visits · 25 rows per page")
            st.dataframe(data["records"]["rows"], use_container_width=True, hide_index=True)
    st.caption("Counts reflect clinic visits, not population prevalence.")
else:
    if not health["agent_configured"]:
        st.warning(
            "Ask the Data needs an OpenRouter API key in the backend configuration. The dashboard remains available."
        )
    with st.container(key="chat-layout"):
        left, right = st.columns([2.5, 1])
        prompt = None
        with left:
            for index, message in enumerate(st.session_state["messages"]):
                with st.chat_message(
                    message["role"], avatar="🩺" if message["role"] == "assistant" else None
                ):
                    st.markdown(message["content"])
                    for j, chart in enumerate(message.get("charts", [])):
                        show_chart(chart, f"message-{index}-{j}")
                    if message.get("steps"):
                        with st.expander("View calculations and applied filters"):
                            for step in message["steps"]:
                                st.write(("✓ " if step["success"] else "⚠ ") + step["label"])
                                st.caption(scope_text(step["filters"]))
            if not st.session_state["messages"]:
                with st.container(border=True):
                    st.subheader("What would you like to explore?")
                    st.write(
                        "Ask about visit counts, trends, groups or comparisons. Answers use your selected dataset."
                    )
            chips = st.columns(3)
            for col, label, question in [
                (
                    chips[0],
                    "Top conditions",
                    "Which recorded conditions account for the most visits? Show a chart.",
                ),
                (chips[1], "Age groups", "Show recorded visits by age band as a chart."),
                (chips[2], "Weekly trends", "Show weekly recorded visit counts as a line chart."),
            ]:
                if col.button(label, disabled=not health["agent_configured"], use_container_width=True):
                    prompt = question
            typed = st.chat_input(
                "Ask a question about your clinic visits…", disabled=not health["agent_configured"]
            )
            prompt = typed or prompt
        with right:
            with st.container(border=True):
                st.subheader("Analysis details")
                last = st.session_state["last_analysis"]
                if last:
                    for step in last["steps"]:
                        st.write(("✓ " if step["success"] else "⚠ ") + step["label"])
                    st.caption("Filters used in the latest answer")
                    for i, step in enumerate(last["steps"]):
                        with st.expander(step["label"] + f" · {i + 1}"):
                            st.write(scope_text(step["filters"]))
                    if not last["steps"]:
                        st.caption("No calculations performed; the agent may be asking for clarification.")
                else:
                    st.caption("Completed analysis steps will appear here.")
                st.divider()
                st.caption("Current selection")
                st.write(scope_text(filters))
                st.caption("Past answers retain the filters used when they were generated.")
            if st.button("Clear conversation"):
                st.session_state["messages"] = []
                st.session_state["last_analysis"] = None
                st.rerun()
        if prompt:
            history = [
                {"role": m["role"], "content": m["content"][:4000]}
                for m in st.session_state["messages"][-12:]
            ]
            try:
                with left, st.spinner("Checking your data and preparing an answer…"):
                    result = api(
                        "POST",
                        "/chat",
                        json={
                            "dataset_id": info["dataset_id"],
                            "question": prompt,
                            "filters": filters,
                            "history": history,
                        },
                    )
                st.session_state["messages"].extend(
                    [
                        {"role": "user", "content": prompt},
                        {
                            "role": "assistant",
                            "content": result["answer"],
                            "charts": result["charts"],
                            "steps": result["steps"],
                        },
                    ]
                )
                st.session_state["messages"] = st.session_state["messages"][-24:]
                st.session_state["last_analysis"] = result
                st.rerun()
            except ApiError as exc:
                with left:
                    st.error(str(exc))
