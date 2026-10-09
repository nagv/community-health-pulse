"""Explore Data: condition table and paginated visit records."""

import math

import streamlit as st

from frontend import state
from frontend.components import kpis

PAGE_SIZE = 25

CONDITION_COLUMNS = {
    "condition": st.column_config.TextColumn("Condition"),
    "visits": st.column_config.NumberColumn("Recorded visits", format="localized"),
    "share_pct": st.column_config.NumberColumn("Share of visits", format="%.1f%%"),
}
RECORD_COLUMNS = {
    "visit_id": st.column_config.TextColumn("Visit ID"),
    "visit_date": st.column_config.DateColumn("Visit date", format="YYYY-MM-DD"),
    "locality": st.column_config.TextColumn("Locality"),
    "age": st.column_config.NumberColumn("Age", format="%d"),
    "age_band": st.column_config.TextColumn("Age band"),
    "gender": st.column_config.TextColumn("Gender"),
    "condition": st.column_config.TextColumn("Condition"),
}


def _go_to(page: int) -> None:
    st.session_state[state.PAGE] = page


def render(data: dict) -> None:
    kpis.render(data["summary"])
    with st.container(border=True):
        st.subheader("Condition breakdown")
        if data["condition_groups"] > len(data["conditions"]):
            st.caption(f"Showing the top 50 of {data['condition_groups']} recorded conditions.")
        st.dataframe(data["conditions"], column_config=CONDITION_COLUMNS, width="stretch", hide_index=True)

    with st.container(border=True):
        st.subheader("Visit records")
        total = data["records"]["total"]
        pages = max(1, math.ceil(total / PAGE_SIZE))
        page = min(st.session_state[state.PAGE], pages)
        prev_col, label_col, next_col = st.columns([1, 2, 1], vertical_alignment="center")
        prev_col.button("← Previous", disabled=page <= 1, on_click=_go_to, args=(page - 1,), width="stretch")
        label_col.markdown(
            f"<div style='text-align:center'>Page <b>{page}</b> of {pages} · {total:,} matching visits</div>",
            unsafe_allow_html=True,
        )
        next_col.button("Next →", disabled=page >= pages, on_click=_go_to, args=(page + 1,), width="stretch")
        st.dataframe(data["records"]["rows"], column_config=RECORD_COLUMNS, width="stretch", hide_index=True)
    st.caption("Counts reflect clinic visits, not population prevalence.")
