from pathlib import Path

from fastapi.testclient import TestClient
from streamlit.testing.v1 import AppTest

from backend.main import app
from frontend import client as api_client


def install_api(monkeypatch):
    client = TestClient(app)

    def local_api(method, path, **kwargs):
        response = client.request(method, path, **kwargs)
        if response.is_error:
            raise api_client.ApiError(str(response.json().get("detail", "Error")), response.status_code)
        return response.json() if response.content else None

    monkeypatch.setattr(api_client, "api", local_api)


def test_upload_empty_state_and_load_dashboard(monkeypatch):
    install_api(monkeypatch)
    at = AppTest.from_file(str(Path(__file__).parents[1] / "frontend" / "app.py")).run(timeout=60)
    assert not at.exception
    assert any("Load demo" in b.label for b in at.button)
    next(b for b in at.button if b.label == "Load demo dataset").click().run(timeout=60)
    assert not at.exception
    assert len(at.metric) == 4
    assert int(at.metric[0].value.replace(",", "")) > 0


def test_chat_missing_key_and_reset_on_dataset_change(monkeypatch):
    install_api(monkeypatch)
    monkeypatch.setenv("OPENROUTER_API_KEY", "")
    at = AppTest.from_file(str(Path(__file__).parents[1] / "frontend" / "app.py")).run(timeout=60)
    next(b for b in at.button if b.label == "Load demo dataset").click().run(timeout=60)
    at.radio[0].set_value("Ask the Data").run(timeout=60)
    assert not at.exception
    assert any("API key" in w.value for w in at.warning)
    at.session_state["messages"] = [{"role": "user", "content": "old question"}]
    at.session_state["last_analysis"] = {"answer": "old"}
    next(b for b in at.button if b.label == "Load demo dataset").click().run(timeout=60)
    assert at.session_state["messages"] == []
    assert at.session_state["last_analysis"] is None


def test_backend_unavailable_is_friendly(monkeypatch):
    def unavailable(*args, **kwargs):
        raise api_client.ApiError("Cannot reach the backend. Start the API service and try again.", 503)

    monkeypatch.setattr(api_client, "api", unavailable)
    at = AppTest.from_file(str(Path(__file__).parents[1] / "frontend" / "app.py")).run(timeout=60)
    assert not at.exception
    assert any("Cannot reach" in item.value for item in at.error)


def test_navigation_updates_workspace_before_dataset_loaded(monkeypatch):
    install_api(monkeypatch)
    at = AppTest.from_file(str(Path(__file__).parents[1] / "frontend" / "app.py")).run(timeout=60)
    for view, heading in [
        ("Explore Data", "Explore recorded visits"),
        ("Ask the Data", "Ask your clinic data"),
        ("Overview", "Clinic activity overview"),
    ]:
        at.radio[0].set_value(view).run(timeout=60)
        assert not at.exception
        assert at.title[0].value == heading
        assert any("Load demo dataset" in item.value for item in at.info)


def test_navigation_switches_loaded_sections_and_preserves_selection(monkeypatch):
    install_api(monkeypatch)
    at = AppTest.from_file(str(Path(__file__).parents[1] / "frontend" / "app.py")).run(timeout=60)
    next(b for b in at.button if b.label == "Load demo dataset").click().run(timeout=60)
    dataset_id = at.session_state["dataset"]["dataset_id"]
    at.multiselect[0].set_value(["Lakeside"]).run(timeout=60)
    at.session_state["messages"] = [{"role": "user", "content": "Keep this conversation"}]
    for view, heading, section in [
        ("Explore Data", "Explore recorded visits", "Visit records"),
        ("Ask the Data", "Ask your clinic data", "Analysis details"),
        ("Overview", "Clinic activity overview", "Data quality"),
    ]:
        at.radio[0].set_value(view).run(timeout=60)
        assert not at.exception
        assert at.title[0].value == heading
        assert any(item.value == section for item in at.subheader)
        assert at.session_state["dataset"]["dataset_id"] == dataset_id
        assert at.multiselect[0].value == ["Lakeside"]
        assert at.session_state["messages"][0]["content"] == "Keep this conversation"


def test_workspace_navigation_is_in_main_and_filters_are_in_sidebar(monkeypatch):
    install_api(monkeypatch)
    at = AppTest.from_file(str(Path(__file__).parents[1] / "frontend" / "app.py")).run(timeout=60)
    assert len(at.sidebar.radio) == 0
    assert at.radio[0].options == ["Overview", "Explore Data", "Ask the Data"]
    next(b for b in at.button if b.label == "Load demo dataset").click().run(timeout=60)
    assert len(at.sidebar.date_input) == 1
    assert len(at.sidebar.multiselect) == 4
    at.sidebar.multiselect[0].set_value(["Lakeside"]).run(timeout=60)
    at.radio[0].set_value("Ask the Data").run(timeout=60)
    assert not at.exception
    assert any("Showing:" in item.value and "Lakeside" in item.value for item in at.info)


def test_chat_renders_tool_chart_and_preserves_original_scope(monkeypatch):
    import streamlit as st

    rendered = []
    original_plotly_chart = st.plotly_chart

    def capture_chart(chart, **kwargs):
        rendered.append((chart, kwargs))
        return original_plotly_chart(chart, **kwargs)

    monkeypatch.setattr(st, "plotly_chart", capture_chart)
    from langchain_core.messages import AIMessage
    from test_agent import ScriptedModel, call

    import backend.agent

    install_api(monkeypatch)
    monkeypatch.setenv("OPENROUTER_API_KEY", "test-not-a-real-key")
    monkeypatch.setattr(
        backend.agent,
        "build_model",
        lambda: ScriptedModel(
            responses=[
                call("get_top_conditions"),
                call(
                    "create_chart",
                    {"result_id": "LAST", "kind": "bar", "x": "condition", "y": "visits"},
                    "two",
                ),
                AIMessage(content="The chart shows computed recorded visit counts."),
            ]
        ),
    )
    at = AppTest.from_file(str(Path(__file__).parents[1] / "frontend" / "app.py")).run(timeout=60)
    next(b for b in at.button if b.label == "Load demo dataset").click().run(timeout=60)
    at.radio[0].set_value("Ask the Data").run(timeout=60)
    at.chat_input[0].set_value("Show top conditions").run(timeout=60)
    assert not at.exception
    assert len(at.session_state["messages"]) == 2
    assert len(at.session_state["last_analysis"]["charts"]) == 1
    chat_chart, options = rendered[-1]
    assert options.get("height") == chat_chart.layout.height
    assert options.get("width") == "stretch"
    assert chat_chart.layout.margin.l >= 100
    assert chat_chart.layout.margin.b >= 64
    original = at.session_state["messages"][-1]["steps"][0]["filters"]
    at.multiselect[0].set_value(["Lakeside"]).run(timeout=60)
    assert not at.exception
    assert at.session_state["messages"][-1]["steps"][0]["filters"] == original


def test_empty_dashboard_selection_and_records_pagination(monkeypatch):
    from datetime import date

    install_api(monkeypatch)
    at = AppTest.from_file(str(Path(__file__).parents[1] / "frontend" / "app.py")).run(timeout=60)
    next(b for b in at.button if b.label == "Load demo dataset").click().run(timeout=60)
    at.radio[0].set_value("Explore Data").run(timeout=60)
    at.number_input[0].set_value(2).run(timeout=60)
    assert not at.exception
    assert at.session_state["page"] == 2
    at.date_input[0].set_value((date(2027, 1, 1), date(2027, 1, 2))).run(timeout=60)
    assert not at.exception
    assert at.metric[0].value == "0"
    assert at.session_state["page"] == 1
