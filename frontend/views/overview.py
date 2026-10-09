"""Overview: KPIs, visit trend, top conditions and localities."""

import json

import pandas as pd
import streamlit as st

from frontend.components import chart, kpis


def render(data: dict) -> None:
    summary = data["summary"]
    kpis.render(summary)
    if not summary["recorded_visits"]:
        st.info("No visits match these filters. Broaden the date range or clear a filter.")

    with st.container(key="overview-primary"):
        left, right = st.columns([1.6, 1])
        for col, result_id, key in [
            (left, "dashboard-trend", "trend"),
            (right, "dashboard-conditions", "conditions"),
        ]:
            spec = chart.find(data["charts"], result_id)
            with col, st.container(border=True):
                st.subheader(spec["title"])
                chart.show(spec, key)
    with st.container(border=True):
        spec = chart.find(data["charts"], "dashboard-localities")
        st.subheader(spec["title"])
        chart.show(spec, "localities")

    csv_col, json_col, _ = st.columns([1, 1, 2])
    csv_col.download_button(
        "Download condition table (CSV)",
        pd.DataFrame(data["conditions"]).to_csv(index=False),
        "clinic-conditions.csv",
        "text/csv",
        width="stretch",
    )
    json_col.download_button(
        "Export full analysis (JSON)",
        json.dumps(data, indent=2),
        "clinic-analysis.json",
        "application/json",
        width="stretch",
    )
    st.caption("Counts reflect clinic visits, not population prevalence.")
