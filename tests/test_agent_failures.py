"""Agent failure states, tool execution limits and tool misuse."""

import httpx
import openai
import pytest
from langchain_core.messages import AIMessage
from test_agent import ScriptedModel
from test_data import CSV

from backend import agent
from backend.agent import AgentFailure, run_chat, tool_error
from backend.analysis import Analysis
from backend.data import validate_csv
from backend.tools import ToolSession
from shared.models import ChatRequest, Filters

REQUEST = httpx.Request("POST", "https://openrouter.ai/api/v1/chat/completions")


@pytest.fixture
def analysis():
    frame, _ = validate_csv(CSV)
    return Analysis(frame)


def status_error(code, cls=openai.APIStatusError):
    return cls("provider says secret-detail", response=httpx.Response(code, request=REQUEST), body=None)


class FailingModel(ScriptedModel):
    error: Exception

    async def _agenerate(self, *args, **kwargs):
        raise self.error


@pytest.mark.parametrize(
    "error,status,message",
    [
        (status_error(401, openai.AuthenticationError), 503, "rejected the API key"),
        (openai.APIConnectionError(request=REQUEST), 502, "Cannot connect to OpenRouter"),
        (status_error(402), 429, "credits or rate limit"),
        (status_error(429, openai.RateLimitError), 429, "credits or rate limit"),
        (status_error(500, openai.InternalServerError), 502, "could not complete this request"),
        (RuntimeError("secret-detail from a library bug"), 502, "could not be completed"),
    ],
    ids=["auth", "connection", "credits", "rate-limit", "server", "unexpected"],
)
async def test_provider_failures_are_sanitised(analysis, error, status, message):
    model = FailingModel(responses=[AIMessage(content="unused")], error=error)
    with pytest.raises(AgentFailure) as exc:
        await run_chat(analysis, ChatRequest(dataset_id="test", question="Count visits"), model=model)
    assert exc.value.status_code == status
    assert message in str(exc.value)
    assert "secret-detail" not in str(exc.value)


async def test_token_usage_is_summed_and_content_blocks_are_joined(analysis):
    model = ScriptedModel(
        responses=[
            AIMessage(
                content="",
                tool_calls=[{"name": "get_dataset_summary", "args": {}, "id": "a"}],
                usage_metadata={"input_tokens": 10, "output_tokens": 2, "total_tokens": 12},
            ),
            AIMessage(
                content=[{"type": "text", "text": "Four recorded"}, {"type": "text", "text": "visits."}],
                usage_metadata={"input_tokens": 20, "output_tokens": 3, "total_tokens": 23},
            ),
        ]
    )
    result = await run_chat(analysis, ChatRequest(dataset_id="test", question="How many?"), model=model)
    assert result.answer == "Four recorded\nvisits."
    assert result.token_usage == {"input_tokens": 30, "output_tokens": 5, "total_tokens": 35}


def test_build_model_uses_bounded_timeouts(monkeypatch):
    monkeypatch.setenv("OPENROUTER_API_KEY", "test-not-a-real-key")
    monkeypatch.setenv("DEFAULT_MODEL", "openai/gpt-4o-mini")
    model = agent.build_model()
    assert model.model_name == "openai/gpt-4o-mini"
    assert model.request_timeout == agent.MODEL_TIMEOUT_S
    assert model.max_retries == agent.MODEL_MAX_RETRIES
    assert model.max_tokens == 1400


def test_tool_error_only_explains_parameter_errors():
    assert "Invalid analysis parameters" in tool_error(ValueError("x"), None)
    assert "Invalid analysis parameters" in tool_error(TypeError("x"), None)
    assert tool_error(RuntimeError("x"), None) is None


async def test_tool_session_caps_executions_including_charts(analysis):
    session = ToolSession(analysis, Filters())
    tools = {t.name: t for t in session.tools()}
    results = [await tools["get_top_conditions"].ainvoke({}) for _ in range(12)]
    with pytest.raises(RuntimeError, match="limit"):
        await tools["get_dataset_summary"].ainvoke({})
    with pytest.raises(RuntimeError, match="limit"):
        await tools["create_chart"].ainvoke(
            {"result_id": results[0]["result_id"], "kind": "bar", "x": "condition", "y": "visits"}
        )


async def test_chart_rejects_mismatched_group_or_measure(analysis):
    session = ToolSession(analysis, Filters())
    tools = {t.name: t for t in session.tools()}
    result = await tools["get_top_conditions"].ainvoke({})
    for x, y in [("locality", "visits"), ("condition", "change")]:
        with pytest.raises(ValueError, match="supported measure"):
            await tools["create_chart"].ainvoke(
                {"result_id": result["result_id"], "kind": "bar", "x": x, "y": y}
            )
    assert session.charts == []


async def test_compare_periods_tool_scopes_dates_and_keeps_other_filters(analysis):
    base = Filters(start_date="2026-07-01", end_date="2026-07-08", localities=["Lakeside"])
    session = ToolSession(analysis, base)
    tool = next(t for t in session.tools() if t.name == "compare_periods")
    result = await tool.ainvoke(
        {
            "previous_start": "2026-07-01",
            "previous_end": "2026-07-02",
            "current_start": "2026-07-08",
            "current_end": "2026-07-08",
            "group": "condition",
        }
    )
    scope = result["filters"]
    assert scope["start_date"] is None and scope["end_date"] is None
    assert scope["previous_period"] == ["2026-07-01", "2026-07-02"]
    assert scope["current_period"] == ["2026-07-08", "2026-07-08"]
    assert scope["localities"] == ["Lakeside"]
    assert result["measures"] == ["previous_visits", "current_visits", "change"]
    rows = {r["condition"]: r for r in result["rows"]}
    # Lakeside has no visits on 1-2 July and one Respiratory visit on 8 July.
    assert rows["Respiratory"]["previous_visits"] == 0 and rows["Respiratory"]["current_visits"] == 1
    assert rows["Respiratory"]["change_pct"] is None  # zero baseline


async def test_compare_periods_tool_rejects_overlap(analysis):
    session = ToolSession(analysis, Filters())
    tool = next(t for t in session.tools() if t.name == "compare_periods")
    with pytest.raises(ValueError, match="overlap"):
        await tool.ainvoke(
            {
                "previous_start": "2026-07-01",
                "previous_end": "2026-07-05",
                "current_start": "2026-07-05",
                "current_end": "2026-07-08",
            }
        )
