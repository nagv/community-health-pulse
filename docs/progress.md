# Week 1 execution ledger

Authority: approved implementation plan in chat.

## Decisions
- Created an independent repository at the requested path, on branch week1; existing projects are untouched.
- ChatOpenAI honours OpenRouter's configurable compatible base URL.
- Dashboard and tool calculations share Analysis; charts reference per-request stored results.
- In-memory datasets have one-hour idle expiry and eight-dataset capacity; documented demo limits.
- Trend timelines intersect the dataset range; grouping displays explicitly report truncation.
- Real hosted-model inference needs the user's backend API key; none was available.

## Completed
- Setup, independent applications and Git initialisation.
- CSV validation, duplicate handling, synthetic data and shared analytics.
- Typed API, six-tool LangChain agent, execution caps, timeout and error sanitisation.
- Streamlit medical-themed Overview, Explore Data and Ask the Data.
- Startup scripts, separate dependency manifests, tested dependency snapshot and Docker examples.
- Read-only independent review; two important edge cases and chart propagation fixed with regressions.
- 36 automated tests passed, including real agent loop with scripted model and five Streamlit AppTests.
- Ruff checks passed.

## Verification limits
- Live OpenRouter smoke check: SKIPPED because OPENROUTER_API_KEY is not configured.
- Browser visual check: blocked by sandbox-local network connectivity. Service startup succeeded at 8501/8000, but browser and cross-process requests timed out.
- Request to launch services outside sandbox was rejected by environment approval policy (sandbox_approval=false). Sandbox preview processes were stopped.
- Run start-backend.ps1 and start-frontend.ps1 from normal local PowerShell windows to view the app.
- Docker deployment examples supplied; images not built or deployed.
