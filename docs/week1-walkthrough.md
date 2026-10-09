# Week 1 walkthrough
1. Load synthetic data and identify the date range, fields, visit count and four localities.
2. Explore the Overview, then narrow a locality and age band. Confirm the count changes.
3. Inspect records on Explore Data and page through them.
4. Enable OpenRouter in backend/.env, restart backend, and ask for top conditions with a chart.
5. Open analysis details: identify the tool choices and computed evidence.
6. Ask for weekly trends and a two-period comparison with explicit dates.
7. Ask an ambiguous comparison; the agent should request dates.
8. Ask for an unavailable field or medical treatment; the agent should explain its limits.
9. Upload an invalid date or conflicting ID and inspect validation feedback.
10. Switch datasets; verify chat resets.

## Course evidence
- AI-assisted UI creation: initial teal medical mockup, implemented dashboard, readable filter layout and sidebar navigation.
- Prompt iteration: documented system rules for aggregate-only answers, explicit periods, effective filters, zero baselines and chart evidence.
- Function calling: six typed predefined tools and a real LangChain tool loop.
- Context windows: bounded question/history and aggregate outputs.
- Cost/reliability: output cap, call/step caps, timeout, transient retries and usage logs.
- Structured output: typed API contracts and chart specifications validated with Pydantic.
- Tools/platforms: Streamlit, pandas, Plotly, FastAPI, LangChain, OpenRouter.
- Model choice: configurable Gemini 2.5 Flash default; live performance must be measured with configured credentials.

## Reusable development instructions
See AGENTS.md for the project's development rules; review AI-generated changes against tests rather than trusting generated calculations.
