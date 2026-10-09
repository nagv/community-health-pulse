"""Ask the Data: chat with the backend agent; every answer keeps the filters it used."""

import streamlit as st

from frontend import client, state
from frontend.components import chart
from frontend.components.filters import scope_text

SUGGESTIONS = [
    ("Top conditions", "Which recorded conditions account for the most visits? Show a chart."),
    ("Age groups", "Show recorded visits by age band as a chart."),
    ("Weekly trends", "Show weekly recorded visit counts as a line chart."),
]


def _steps(steps: list[dict]) -> None:
    for step in steps:
        st.write(("✓ " if step["success"] else "⚠ ") + step["label"])
        st.caption(scope_text(step["filters"]))
    if not steps:
        st.caption("No calculations were performed; the assistant may be asking for clarification.")


def _history() -> None:
    for index, message in enumerate(st.session_state[state.MESSAGES]):
        with st.chat_message(message["role"], avatar="🩺" if message["role"] == "assistant" else None):
            st.markdown(message["content"])
            for j, spec in enumerate(message.get("charts", [])):
                chart.show(spec, f"message-{index}-{j}")
            if message["role"] == "assistant":
                with st.expander("View calculations and applied filters"):
                    _steps(message.get("steps", []))


def _ask(info: dict, filters: dict, prompt: str) -> None:
    history = [
        {"role": m["role"], "content": m["content"][:4000]}
        for m in st.session_state[state.MESSAGES][-state.MAX_HISTORY_SENT :]
    ]
    with st.chat_message("user"):
        st.markdown(prompt)
    with st.status("Running analysis tools… answers usually take 10–30 seconds.", expanded=False) as status:
        try:
            result = client.api(
                "POST",
                "/chat",
                json={
                    "dataset_id": info["dataset_id"],
                    "question": prompt,
                    "filters": filters,
                    "history": history,
                },
            )
        except client.ApiError as exc:
            status.update(label="The assistant could not answer", state="error", expanded=True)
            st.error(str(exc))
            return
        status.update(label="Done", state="complete")
    messages = st.session_state[state.MESSAGES]
    messages.extend(
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
    st.session_state[state.MESSAGES] = messages[-state.MAX_STORED_MESSAGES :]
    st.session_state[state.LAST_ANALYSIS] = result
    st.rerun()


def render(info: dict, filters: dict, agent_configured: bool) -> None:
    if not agent_configured:
        st.warning(
            "Ask the Data needs an OpenRouter API key in the backend configuration. The dashboard remains available."
        )
    with st.container(key="chat-layout"):
        left, right = st.columns([2.5, 1])
        prompt = None
        with left:
            _history()
            if not st.session_state[state.MESSAGES]:
                with st.container(border=True):
                    st.subheader("What would you like to explore?")
                    st.write(
                        "Ask about visit counts, trends, groups or comparisons. Answers use your selected data."
                    )
                for col, (label, question) in zip(st.columns(len(SUGGESTIONS)), SUGGESTIONS):
                    if col.button(label, disabled=not agent_configured, width="stretch"):
                        prompt = question
            typed = st.chat_input("Ask a question about your clinic visits…", disabled=not agent_configured)
            prompt = typed or prompt
        with right:
            with st.container(border=True):
                st.subheader("Current selection")
                st.write(scope_text(filters))
                st.caption(
                    "New questions use this selection unless you name other dates or groups. "
                    "Past answers keep the filters they were generated with; open "
                    "“View calculations” under an answer to see them."
                )
            if st.session_state[state.MESSAGES] and st.button("Clear conversation", width="stretch"):
                state.clear_chat()
                st.rerun()
        if prompt:
            with left:
                _ask(info, filters, prompt)
