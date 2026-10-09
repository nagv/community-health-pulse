# Community Health Pulse
A week 1 training project: clinic-visit analytics and a LangChain agent with six predefined tools. Streamlit frontend and FastAPI backend live in one repository and can run independently.

## Local setup (Windows / PowerShell)
Requires Python 3.12+ and either uv or Python's pip.

From this repository:
```powershell
uv venv --python 3.12
uv pip install --python .venv\Scripts\python.exe -r requirements-dev.txt
Copy-Item backend\.env.example backend\.env
Copy-Item frontend\.env.example frontend\.env
```
Add your key to **backend/.env** using your editor. Never paste it into chat or commit it.
```dotenv
OPENROUTER_BASE_URL=https://openrouter.ai/api/v1
DEFAULT_MODEL=google/gemini-2.5-flash
OPENROUTER_API_KEY=
```
Without a key the complete dashboard still works; chat clearly explains the missing configuration.

Start both services from a normal local PowerShell terminal (not a sandbox preview):
```powershell
.venv\Scripts\python.exe run_local.py
```
Keep that terminal open; Ctrl+C stops both apps. Alternatively, open two terminals at the repository root:
```powershell
.\start-backend.ps1
```
```powershell
.\start-frontend.ps1
```
Visit http://localhost:8501. API docs: http://localhost:8000/docs.
If script execution is restricted, use the equivalent Python commands in the frontend/backend READMEs.

## Try it
1. Select **Load demo dataset**.
2. Explore the Overview KPIs and charts. In the sidebar, pick a quick range (e.g. Last 30 days) or From/To dates, adjust locality, condition or age, then press **Apply filters**. Visit counts show the change against the equally long period before the selection.
3. Open **Explore Data** to inspect condition counts and page through records with Previous/Next.
4. With an OpenRouter key configured, open **Ask the Data**.
5. Ask: “Which recorded conditions account for the most visits? Show a chart.”
6. Open **View calculations and applied filters** under the answer; the **Current selection** card shows the filters new questions will use.
7. Ask a follow-up with explicit dates: “Compare Fever visits during 2026-07-01 to 2026-07-07 against 2026-07-08 to 2026-07-14.”
8. Switch datasets and observe that the conversation resets.

## CSV contract
UTF-8 CSV, at most 10 MiB and 100,000 rows:
```csv
visit_id,visit_date,locality,age,gender,condition
v001,2026-07-01,Northstead,8,Female,Respiratory
```
Dates must be valid YYYY-MM-DD dates; age is a whole number from 0 to 120. All six fields are required and at most 200 characters. Additional columns are discarded. Exact duplicate visits are removed after whitespace and type normalisation; conflicting duplicate visit IDs reject the entire file. Validation issues appear in the UI before a dataset is accepted.

A complete tested-environment dependency snapshot is provided in requirements-lock.txt; install it instead of requirements-dev.txt to reproduce these versions.

The reproducible sample is in **data/synthetic_visits.csv**. Its seed is 42; it has 90 days, four localities and five broad recorded-condition categories. Regenerate with:
```powershell
.venv\Scripts\python.exe -m data.generate_sample
```

## Design and limits
- Backend calculates dashboard results and agent tool results with the same pandas functions.
- Tools: summary, top conditions, visit trend, period comparison, group breakdown and chart creation.
- Charts reference a previous tool result; the model cannot provide arbitrary values.
- Week 1 uses one LangChain agent. RAG, multi-agent orchestration and local-model training belong to later weeks.
- Six logical model calls, twelve tool calls, 60-second request deadline, a 15-second timeout and one SDK retry per model call (so a retried call still fits the deadline), and 1,400 output tokens per model call. Retries can make additional provider attempts.
- At most 12 conversation messages are sent per request. Only aggregate tool results and question/history are sent to OpenRouter; visit records and visit IDs are not sent by tools.
- Dashboard condition/locality displays show the top 50 groups with an explicit notice when truncated. Tool summaries show at most 50 groups; trend responses show at most 100 periods. Charts use stored computed results. Weekly buckets start on Monday. Trend timelines are clipped to the available dataset date range.
- Comparison periods are inclusive and must not overlap. They replace UI date limits, while other filters persist. Percent change is undefined at a zero baseline; visit shares are computed within each period.
- Accepted-row completeness is 100% by construction; invalid rows reject a file. It is not a clinical-quality score.
- Dataset IDs are opaque; records are held in one backend process, expire after one idle hour, and clear on restart. At most eight datasets are retained; the oldest is evicted when loading a ninth.
- No clinical recommendations, diagnoses inferred from symptoms, forecasts or prevalence claims. Counts are recorded visits, including repeat visits.
- This is a local synthetic-data prototype. Opaque IDs are not authentication; no public patient-data deployment is included. Do not expose the API publicly without implementing authentication and tenancy.
- Generated prose is model output and can still be inaccurate; inspect the provided calculations. Week 5 adds broader quality evaluations.

## Test and quality checks
```powershell
.venv\Scripts\python.exe -m pytest -q
.venv\Scripts\python.exe -m ruff check .
.venv\Scripts\python.exe -m backend.smoke_check
```
The smoke check is an optional real, potentially billable OpenRouter tool call. It exits with a clear skip message if no key is configured. Unit/integration tests run without a live model.

## Separate deployments
See frontend/README.md and backend/README.md. Docker build contexts are the repository root. For a local two-container example, create backend/.env and run:
```powershell
docker compose up --build
```
Frontend BACKEND_URL points to the backend's reachable address. Backend is single-worker because datasets are in memory; frontend never receives the model key. Docker configuration is supplied as an example and needs Docker installed.

See docs/week1-walkthrough.md for learning objectives and docs/architecture.md for API contracts.
