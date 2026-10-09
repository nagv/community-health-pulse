import asyncio
import json

import pytest
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import AIMessage
from langchain_core.outputs import ChatGeneration, ChatResult
from pydantic import PrivateAttr
from test_data import CSV

from backend.agent import AgentFailure, run_chat
from backend.analysis import Analysis
from backend.data import validate_csv
from backend.tools import ToolSession
from shared.models import ChatRequest, Filters


class ScriptedModel(BaseChatModel):
    responses: list[AIMessage]
    _index: int = PrivateAttr(default=0)

    @property
    def _llm_type(self):
        return "scripted-test"

    def bind_tools(self, tools, **kwargs):
        return self

    def _generate(self, messages, stop=None, run_manager=None, **kwargs):
        # Chart calls reference the result returned by the real analysis tool.
        response = self.responses[min(self._index, len(self.responses) - 1)].model_copy(deep=True)
        self._index += 1
        for call in response.tool_calls:
            if call["name"] == "create_chart" and call["args"].get("result_id") == "LAST":
                results = [m for m in messages if m.type == "tool"]
                call["args"]["result_id"] = json.loads(results[-1].content)["result_id"]
        return ChatResult(generations=[ChatGeneration(message=response)])

    async def _agenerate(self, messages, stop=None, run_manager=None, **kwargs):
        return self._generate(messages, stop, run_manager, **kwargs)


def call(name, args=None, ident="one"):
    return AIMessage(content="", tool_calls=[{"name": name, "args": args or {}, "id": ident}])


@pytest.fixture
def analysis():
    frame, _ = validate_csv(CSV)
    return Analysis(frame)


async def test_real_agent_executes_analysis_then_chart(analysis):
    model = ScriptedModel(
        responses=[
            call("get_top_conditions"),
            call(
                "create_chart", {"result_id": "LAST", "kind": "bar", "x": "condition", "y": "visits"}, "two"
            ),
            AIMessage(content="Respiratory: 2 of 4 recorded visits (50%)."),
        ]
    )
    result = await run_chat(
        analysis, ChatRequest(dataset_id="test", question="Show top conditions"), model=model
    )
    assert "2 of 4" in result.answer
    assert len(result.charts) == 1
    assert result.charts[0].rows[0]["visits"] == 2
    assert all(step.success for step in result.steps)
    assert len(result.steps) == 2


async def test_tools_match_dashboard_and_preserve_filters(analysis):
    session = ToolSession(analysis, Filters(localities=["Lakeside"]))
    tool = next(t for t in session.tools() if t.name == "get_top_conditions")
    result = await tool.ainvoke({})
    assert result["rows"] == analysis.top_conditions(Filters(localities=["Lakeside"]))
    assert result["filters"]["localities"] == ["Lakeside"]
    overridden = await tool.ainvoke({"filters": {"localities": ["Northstead"]}})
    assert overridden["filters"]["localities"] == ["Northstead"]
    assert session.steps[-1].filters["localities"] == ["Northstead"]


async def test_chart_cannot_invent_data(analysis):
    session = ToolSession(analysis, Filters())
    chart = next(t for t in session.tools() if t.name == "create_chart")
    with pytest.raises(ValueError):
        await chart.ainvoke({"result_id": "invented", "kind": "bar", "x": "condition", "y": "visits"})


async def test_unsupported_question_can_ask_for_clarification(analysis):
    model = ScriptedModel(responses=[AIMessage(content="Please specify the two date ranges to compare.")])
    result = await run_chat(analysis, ChatRequest(dataset_id="test", question="Compare periods"), model=model)
    assert "specify" in result.answer
    assert result.charts == [] and result.steps == []


async def test_model_call_limit(analysis):
    model = ScriptedModel(responses=[call("get_dataset_summary")])
    with pytest.raises(AgentFailure) as exc:
        await run_chat(analysis, ChatRequest(dataset_id="test", question="Loop"), model=model)
    assert exc.value.status_code == 429


async def test_tool_call_limit(analysis):
    calls = [{"name": "get_dataset_summary", "args": {}, "id": str(i)} for i in range(13)]
    model = ScriptedModel(responses=[AIMessage(content="", tool_calls=calls)])
    with pytest.raises(AgentFailure) as exc:
        await run_chat(analysis, ChatRequest(dataset_id="test", question="Many tools"), model=model)
    assert exc.value.status_code == 429


async def test_timeout_cancels_request(analysis):
    class SlowModel(ScriptedModel):
        async def _agenerate(self, *args, **kwargs):
            await asyncio.sleep(5)
            return await super()._agenerate(*args, **kwargs)

    with pytest.raises(AgentFailure) as exc:
        await run_chat(
            analysis,
            ChatRequest(dataset_id="test", question="Slow"),
            model=SlowModel(responses=[AIMessage(content="late")]),
            timeout=0.01,
        )
    assert exc.value.status_code == 504


async def test_missing_key_is_clear_and_no_fake_reply(analysis, monkeypatch):
    monkeypatch.setenv("OPENROUTER_API_KEY", "")
    with pytest.raises(AgentFailure) as exc:
        await run_chat(analysis, ChatRequest(dataset_id="test", question="Count visits"))
    assert exc.value.status_code == 503
    assert "OPENROUTER_API_KEY" in str(exc.value)


async def test_unknown_tools_are_not_executed(analysis):
    model = ScriptedModel(
        responses=[
            call("execute_python", {"code": "print('bad')"}),
            AIMessage(content="I can only use approved analysis tools."),
        ]
    )
    result = await run_chat(analysis, ChatRequest(dataset_id="test", question="Execute code"), model=model)
    assert result.steps == []
    assert "approved" in result.answer


async def test_agent_chart_reports_truncated_groups_and_full_trends():
    from datetime import date, timedelta

    rows = b"visit_id,visit_date,locality,age,gender,condition\n"
    rows += b"".join(
        f"v{i},{date(2026, 7, 1) + timedelta(days=i)},L{i},30,Female,C{i}\n".encode() for i in range(55)
    )
    frame, _ = validate_csv(rows)
    session = ToolSession(Analysis(frame), Filters())
    tools = {t.name: t for t in session.tools()}
    groups = await tools["get_group_breakdown"].ainvoke({"group": "locality"})
    await tools["create_chart"].ainvoke(
        {"result_id": groups["result_id"], "kind": "bar", "x": "locality", "y": "visits"}
    )
    assert session.charts[-1].truncated is True
    assert session.charts[-1].total_groups == 55
    trend = await tools["get_visit_trend"].ainvoke({"frequency": "daily"})
    await tools["create_chart"].ainvoke(
        {"result_id": trend["result_id"], "kind": "line", "x": "period", "y": "visits"}
    )
    assert session.charts[-1].truncated is False
    assert len(session.charts[-1].rows) == 55


async def test_failed_tool_is_visible_without_disclosing_arguments(analysis):
    model = ScriptedModel(
        responses=[
            call(
                "create_chart",
                {"result_id": "private-injected-value", "kind": "bar", "x": "condition", "y": "visits"},
            ),
            AIMessage(content="No valid analysis result is available for that chart."),
        ]
    )
    result = await run_chat(analysis, ChatRequest(dataset_id="test", question="Try a chart"), model=model)
    assert len(result.steps) == 1
    assert result.steps[0].success is False
    assert "private-injected-value" not in result.steps[0].label
    assert result.charts == []


def test_model_retries_fit_inside_request_deadline():
    from backend import agent

    # Leave room for at least one more model call and the tool work within the deadline.
    assert agent.MODEL_TIMEOUT_S * agent.MODEL_ATTEMPTS < agent.REQUEST_TIMEOUT_S
