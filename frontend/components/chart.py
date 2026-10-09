"""Render a backend ChartSpec with Streamlit."""

import hashlib

import streamlit as st

from frontend.charts import figure


def find(charts: list[dict], result_id: str) -> dict:
    """Look a dashboard chart up by its result_id instead of its list position."""
    return next(chart for chart in charts if chart["result_id"] == result_id)


def show(spec: dict, key: str) -> None:
    if spec.get("truncated"):
        st.caption(
            f"Showing the first {len(spec['rows'])} of {spec['total_groups']} groups. "
            "Totals include all matching visits."
        )
    chart = figure(spec)
    if chart is None:
        st.info("No visits match this selection.")
        return
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
