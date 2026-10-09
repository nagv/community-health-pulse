"""Sidebar filter form: quick ranges, From/To dates and group filters, applied on demand.

Widgets live in an st.form, so the dashboard and backend are only recalculated
when "Apply filters" is pressed. Keys are suffixed with the dataset ID so each
dataset starts from its own full range.
"""

from datetime import date, timedelta

import streamlit as st

PRESETS = {
    "All dates": None,
    "Last 7 days": 7,
    "Last 30 days": 30,
    "Last 90 days": 90,
    "Custom range": "custom",
}
FIELDS = ("preset", "start", "end", "localities", "ages", "conditions", "genders")


def _key(name: str, dataset_id: str) -> str:
    return f"{name}_{dataset_id}"


def preset_range(preset: str, first: date, last: date) -> tuple[date, date] | None:
    """Dates for a quick range, counted back from the dataset's last date; None for a custom range."""
    days = PRESETS.get(preset)
    if days == "custom":
        return None
    if days is None:
        return first, last
    return max(first, last - timedelta(days=days - 1)), last


def defaults(info) -> dict:
    return {
        "preset": "All dates",
        "start": date.fromisoformat(info["start_date"]),
        "end": date.fromisoformat(info["end_date"]),
        "localities": [],
        "ages": [],
        "conditions": [],
        "genders": [],
    }


def reset(session, dataset_id: str, values: dict) -> None:
    for name in FIELDS:
        session[_key(name, dataset_id)] = values[name]
    session[_key("applied_dates", dataset_id)] = (values["start"], values["end"])


def apply_preset(session, dataset_id: str, first: date, last: date) -> None:
    """Apply-button callback: turn a preset into dates; edited dates win and switch to Custom."""
    k = lambda name: _key(name, dataset_id)
    picked = (session[k("start")], session[k("end")])
    if picked != session.get(k("applied_dates"), picked):
        session[k("preset")] = "Custom range"
    rng = preset_range(session[k("preset")], first, last)
    if rng is not None:
        session[k("start")], session[k("end")] = rng
    session[k("applied_dates")] = (session[k("start")], session[k("end")])


def render(info) -> dict:
    """Draw the filter form in the sidebar and return the applied filters as an API payload."""
    sid = info["dataset_id"]
    first, last = date.fromisoformat(info["start_date"]), date.fromisoformat(info["end_date"])
    base = defaults(info)
    if _key("preset", sid) not in st.session_state:
        reset(st.session_state, sid, base)

    with st.sidebar, st.container(key="filters"), st.form(f"filter-form-{sid}", border=False):
        st.subheader("Filters")
        st.selectbox(
            "Quick range",
            list(PRESETS),
            key=_key("preset", sid),
            help="Counted back from the latest visit date. Choose “Custom range” to use the dates below.",
        )
        start_col, end_col = st.columns(2)
        start_col.date_input("From", min_value=first, max_value=last, key=_key("start", sid))
        end_col.date_input("To", min_value=first, max_value=last, key=_key("end", sid))
        st.multiselect(
            "Locality", info["localities"], placeholder="All localities", key=_key("localities", sid)
        )
        st.multiselect("Age band", info["age_bands"], placeholder="All ages", key=_key("ages", sid))
        st.multiselect(
            "Condition", info["conditions"], placeholder="All conditions", key=_key("conditions", sid)
        )
        with st.expander("Additional filters"):
            st.multiselect("Gender", info["genders"], placeholder="All genders", key=_key("genders", sid))
        apply_col, reset_col = st.columns(2)
        apply_col.form_submit_button(
            "Apply filters",
            type="primary",
            width="stretch",
            on_click=apply_preset,
            args=(st.session_state, sid, first, last),
        )
        reset_col.form_submit_button(
            "Reset", width="stretch", on_click=reset, args=(st.session_state, sid, base)
        )

    ss = st.session_state
    start, end = ss[_key("start", sid)], ss[_key("end", sid)]
    if start > end:
        st.sidebar.warning("“From” was after “To”, so the dates were swapped.")
        start, end = end, start
    return {
        "start_date": start.isoformat(),
        "end_date": end.isoformat(),
        "localities": list(ss[_key("localities", sid)]),
        "age_bands": list(ss[_key("ages", sid)]),
        "conditions": list(ss[_key("conditions", sid)]),
        "genders": list(ss[_key("genders", sid)]),
    }


def summary_line(filters: dict, visits: int) -> str:
    start, end = date.fromisoformat(filters["start_date"]), date.fromisoformat(filters["end_date"])
    return (
        f"**Showing:** {start:%d %b %Y} – {end:%d %b %Y}"
        f" · {', '.join(filters['localities']) or 'All localities'}"
        f" · {', '.join(filters['age_bands']) or 'All ages'}"
        f" · {', '.join(filters['conditions']) or 'All conditions'}"
        f" · {', '.join(filters['genders']) or 'All genders'}"
        f" · **{visits:,} recorded visits**"
    )


def scope_text(scope: dict) -> str:
    """Readable description of the filters an analysis step used."""
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
