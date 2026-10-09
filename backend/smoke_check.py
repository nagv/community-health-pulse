"""Optional billable smoke test; never prints keys or raw provider errors."""

import asyncio

from backend.agent import AgentFailure, configured, run_chat
from backend.analysis import Analysis
from backend.data import sample_csv, validate_csv
from shared.models import ChatRequest


async def main():
    if not configured():
        print("SKIPPED: OPENROUTER_API_KEY is not configured.")
        return
    frame, _ = validate_csv(sample_csv())
    try:
        result = await run_chat(
            Analysis(frame),
            ChatRequest(
                dataset_id="smoke",
                question="Use get_top_conditions to find the top recorded condition. "
                "Use create_chart to make a bar chart.",
            ),
        )
    except AgentFailure as exc:
        print(f"FAILED: {exc}")
        raise SystemExit(1) from None
    if len(result.steps) < 2 or not result.charts:
        print("FAILED: model did not complete analysis and chart tool calls.")
        raise SystemExit(1)
    print(
        f"PASSED: {len(result.steps)} completed tools; {len(result.charts)} chart; "
        f"{result.duration_ms} ms; tokens={result.token_usage}."
    )


if __name__ == "__main__":
    asyncio.run(main())
