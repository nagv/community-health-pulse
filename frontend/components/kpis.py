"""Headline KPI cards for the Overview and Explore views."""

import streamlit as st


def _change(summary: dict) -> str | None:
    if summary.get("change_pct") is None:
        return None
    return f"{summary['change_pct']:+.1f}% vs previous {summary['previous_period_visits']:,}"


def render(summary: dict) -> None:
    top = summary.get("top_condition")
    share = summary.get("top_condition_share_pct")
    cards = [
        ("Recorded visits", f"{summary['recorded_visits']:,}", _change(summary)),
        ("Avg visits per day", f"{summary.get('avg_visits_per_day', 0):,.1f}", None),
        ("Top condition", top or "—", f"{share:.1f}% of visits" if share is not None else None),
        ("Busiest locality", summary.get("busiest_locality") or "—", None),
    ]
    with st.container(key="metrics"):
        for col, (label, value, delta) in zip(st.columns(len(cards)), cards):
            # The top-condition share is context, not a change, so it is shown without colour.
            col.metric(label, value, delta=delta, delta_color="off" if label == "Top condition" else "normal")
    if summary.get("previous_period_visits") is None:
        st.caption("No change shown: the equally long period before this selection is outside the dataset.")
    else:
        st.caption("Change compares with the equally long period immediately before the selected dates.")
