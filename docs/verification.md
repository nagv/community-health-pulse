# Week 1 verification

Automated verification: **36 passed**.
Static checks: **Ruff passed**.

Tests cover CSV schema and date validation, integer age bounds, missing values, file/row limits, duplicate behaviour, reproducible data, count/share calculations, filtering, zero-filled trends, zero-baseline comparisons, extreme requested dates, chart truncation and pagination.

Agent tests invoke the real LangChain create_agent graph using a deterministic scripted chat model. They cover multi-step analysis/chart calls, dataset-bound tools, effective filter overrides, unsupported tools, clarification responses, invalid chart sources, tool failure feedback, model/tool call limits and timeout cancellation.

FastAPI integration tests exercise dataset creation, metadata, filtered dashboard, validation failures, deletion, health and missing-key behaviour.
Five Streamlit AppTests cover initial state, demo loading, dashboard metrics, chat missing-key state, dataset-switch chat reset, backend error messages, generated chat charts, preserved historical filters, pagination and empty selections.

Optional live check:
```powershell
.venv\Scripts\python.exe -m backend.smoke_check
```
Actual result: SKIPPED, no OpenRouter key configured. Tests are not evidence of the hosted model's actual accuracy.

The app processes started successfully on 8000 and 8501; sandbox cross-process connections timed out, including the in-app browser. An outside-sandbox launch was rejected by environment approval policy. Preview processes were stopped. Browser rendering remains unverified. Launch both services from normal PowerShell windows using the supplied scripts to review the UI.

Independent read-only review found two issues: extreme date filters and unannounced category truncation. Both, plus agent chart metadata propagation, have regression tests and were fixed.

Docker examples were not built or deployed.
