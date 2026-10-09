# Frontend
Install frontend/requirements.txt in its own Python 3.12 environment.
Copy .env.example to .env; set BACKEND_URL to the backend address.
From the frontend folder:
```powershell
python -m streamlit run app.py --server.port 8501 --server.headless true
```
The UI reads and writes data only through HTTP API calls. It never receives an LLM key. Changing datasets clears chat, filters and the current analysis. Existing chat answers keep their original filter details when UI filters change.

Container build from repository root:
```text
docker build -f frontend/Dockerfile -t health-pulse-frontend .
```
Set BACKEND_URL in the hosting environment. Streamlit calls the API from its server, so browser CORS configuration is unnecessary for this setup.
