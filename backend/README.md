# Backend
Install backend/requirements.txt into a separate Python 3.12 environment.
From repository root:
```powershell
python -m uvicorn backend.main:app --host 127.0.0.1 --port 8000
```
Configure backend/.env from .env.example (or set environment secrets):
OPENROUTER_API_KEY, OPENROUTER_BASE_URL, DEFAULT_MODEL.
The key is required only for /chat.

For container deployment, from repository root:
```text
docker build -f backend/Dockerfile -t health-pulse-backend .
```
Use one worker and one backend instance. In-memory dataset IDs cannot be shared between replicas. Restart clears data. /health reports readiness and whether an LLM key is configured, without returning its value. /docs provides generated OpenAPI documentation. Logs include durations, reported token counts and successful tool labels, never questions, CSV rows or secrets.

When deployed publicly, set BACKEND_API_TOKEN to a long random value: every route except /health then requires a matching X-API-Token header (the frontend sends it from its own BACKEND_API_TOKEN). Leave it unset for local development.
