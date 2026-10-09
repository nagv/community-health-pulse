# Architecture and contracts

Streamlit → FastAPI → shared Analysis functions → in-memory dataset.
For chat: FastAPI → LangChain create_agent → OpenRouter model → predefined tools → computed results.
Streamlit builds Plotly figures from validated chart specifications.

## HTTP API
| Method | Path | Behaviour |
|---|---|---|
| GET | /health | API state and agent_configured boolean |
| POST | /datasets | multipart file; validates before storing; 201 DatasetInfo |
| POST | /datasets/sample | load reproducible synthetic data; 201 DatasetInfo |
| GET | /datasets/{id} | dataset metadata and validation report |
| DELETE | /datasets/{id} | idempotent removal; 204 |
| POST | /datasets/{id}/analysis | filters, page and page_size; summary, charts and records |
| POST | /chat | dataset_id, question, filters, history; answer, charts, steps, usage and duration |

The typed source of truth is shared/models.py. /openapi.json documents exact schemas.
Filters contain optional start/end dates and lists of localities, age_bands, conditions and genders.
Empty lists mean all values. Age bands: 0–4, 5–17, 18–44, 45–64, 65+.
Missing dataset IDs return 404. CSV issues return 422. Unconfigured model returns 503.
Provider errors return 502, provider credits/rate/agent limits return 429, timeout returns 504.
Only user and assistant roles are accepted in bounded history.

Tools are bound to the selected dataset; they cannot select other datasets. Partial explicit filter overrides merge over the active UI filters. Comparison dates replace UI date bounds; every tool result and rendered chart includes effective scope.
Chart tools require an existing per-request result ID, its grouping column and an approved numerical measure.

## Trust and operational boundary
Treat CSV labels and model output as untrusted. No eval/exec, arbitrary SQL, browser, filesystem, prescribing, or raw-record retrieval tool is present.
System prompts guide prose; they do not prove its correctness. Calculated evidence and charts can be inspected independently.
The prototype has no production authentication or per-user tenancy. Run locally with synthetic data.
No automated real patient-data approval, vaccine or medicine planning is implemented.
