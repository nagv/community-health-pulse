"""Sidebar dataset controls: upload, demo data, dataset details and clearing."""

import streamlit as st

from frontend import client, state


def _load(action, success: str | None = None) -> None:
    try:
        state.replace_dataset(action())
        if success:
            st.success(success)
        st.rerun()
    except client.ApiError as exc:
        st.error(str(exc))


def render() -> None:
    with st.sidebar:
        st.markdown(
            '<div class="brand"><span>⌁</span>Community<br>Health Pulse</div>', unsafe_allow_html=True
        )
        st.caption("YOUR DATASET")
        uploaded = st.file_uploader(
            "Upload clinic CSV", type=["csv"], help="UTF-8 CSV, up to 10 MB / 100,000 visits."
        )
        if st.button("Validate and load CSV", disabled=uploaded is None, width="stretch"):
            with st.spinner("Validating your CSV…"):
                _load(
                    lambda: client.api(
                        "POST", "/datasets", files={"file": (uploaded.name, uploaded.getvalue(), "text/csv")}
                    ),
                    "Dataset accepted.",
                )
        if st.button("Load demo dataset", type="primary", width="stretch"):
            with st.spinner("Loading synthetic visits…"):
                _load(lambda: client.api("POST", "/datasets/sample"))

        info = st.session_state[state.DATASET]
        if not info:
            st.caption("Week 1 · Clinic analytics")
            return
        st.caption(info["name"])
        st.caption(f"{info['row_count']:,} accepted visits")
        st.markdown("**Synthetic demo data**" if info["synthetic"] else "**Uploaded dataset**")
        with st.expander("Dataset details"):
            report = info["validation"]
            st.write("All accepted rows passed validation.")
            st.write(f"{report['duplicates_removed']:,} exact duplicates removed")
            st.caption(f"{report['input_rows']:,} input rows · {report['accepted_rows']:,} accepted rows")
            for warning in report["warnings"]:
                st.warning(warning)
            st.caption("Visit counts can include repeat visits by the same person.")
        if st.button("Clear dataset", width="stretch"):
            try:
                client.api("DELETE", f"/datasets/{info['dataset_id']}")
                state.replace_dataset(None)
                st.rerun()
            except client.ApiError as exc:
                st.error(str(exc))


def footer() -> None:
    with st.sidebar:
        st.divider()
        st.caption("Week 1 · Clinic analytics")
        st.caption("Counts reflect recorded visits, not population prevalence.")
