"""Frontend flows: CSV upload, clearing data, chat errors, suggestions and clearing chat."""

from pathlib import Path

import openai
from langchain_core.messages import AIMessage
from streamlit.testing.v1 import AppTest
from test_agent import ScriptedModel, call
from test_agent_failures import FailingModel, status_error
from test_data import CSV
from test_frontend import install_api, load_demo

import backend.agent

APP = str(Path(__file__).parents[1] / "frontend" / "app.py")


def start(monkeypatch, key="test-not-a-real-key"):
    install_api(monkeypatch)
    monkeypatch.setenv("OPENROUTER_API_KEY", key)
    at = AppTest.from_file(APP).run(timeout=60)
    assert not at.exception
    return at


def test_valid_csv_upload_loads_dataset(monkeypatch):
    at = start(monkeypatch)
    at.sidebar.file_uploader[0].set_value(("visits.csv", CSV, "text/csv")).run(timeout=60)
    next(b for b in at.button if b.label == "Validate and load CSV").click().run(timeout=60)
    assert not at.exception
    info = at.session_state["dataset"]
    assert info["row_count"] == 4 and info["synthetic"] is False
    assert at.metric[0].value == "4"


def test_invalid_csv_upload_shows_issues_and_keeps_empty_state(monkeypatch):
    at = start(monkeypatch)
    bad = CSV.replace(b",8,", b",121,")
    at.sidebar.file_uploader[0].set_value(("bad.csv", bad, "text/csv")).run(timeout=60)
    next(b for b in at.button if b.label == "Validate and load CSV").click().run(timeout=60)
    assert not at.exception
    assert at.session_state["dataset"] is None
    assert any("age" in e.value for e in at.error)


def test_clear_dataset_returns_to_empty_state(monkeypatch):
    at = start(monkeypatch)
    load_demo(at)
    next(b for b in at.button if b.label == "Clear dataset").click().run(timeout=60)
    assert not at.exception
    assert at.session_state["dataset"] is None
    assert any("Load demo dataset" in i.value for i in at.info)


def test_dataset_warnings_are_shown_in_details(monkeypatch):
    at = start(monkeypatch)
    load_demo(at)
    at.session_state["dataset"]["validation"]["warnings"] = ["Additional columns were ignored."]
    at.run(timeout=60)
    assert any("Additional columns" in w.value for w in at.sidebar.warning)


def test_chat_provider_error_is_shown_without_adding_messages(monkeypatch):
    at = start(monkeypatch)
    error = status_error(401, openai.AuthenticationError)
    monkeypatch.setattr(
        backend.agent, "build_model", lambda: FailingModel(responses=[AIMessage(content="x")], error=error)
    )
    load_demo(at)
    at.radio[0].set_value("Ask the Data").run(timeout=60)
    at.chat_input[0].set_value("How many visits?").run(timeout=60)
    assert not at.exception
    assert any("rejected the API key" in e.value for e in at.error)
    assert at.session_state["messages"] == []


def test_suggestion_chip_asks_question_and_clear_conversation(monkeypatch):
    at = start(monkeypatch)
    monkeypatch.setattr(
        backend.agent,
        "build_model",
        lambda: ScriptedModel(
            responses=[call("get_top_conditions"), AIMessage(content="Respiratory leads recorded visits.")]
        ),
    )
    load_demo(at)
    at.radio[0].set_value("Ask the Data").run(timeout=60)
    next(b for b in at.button if b.label == "Top conditions").click().run(timeout=60)
    assert not at.exception
    messages = at.session_state["messages"]
    assert messages[0]["content"].startswith("Which recorded conditions")
    assert messages[1]["content"] == "Respiratory leads recorded visits."
    next(b for b in at.button if b.label == "Clear conversation").click().run(timeout=60)
    assert at.session_state["messages"] == []
    assert at.session_state["last_analysis"] is None
