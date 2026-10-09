# Community Health Pulse development
- Week 1 scope: CSV analytics, Streamlit UI, one LangChain agent with predefined tools.
- Keep the model API key in backend secrets; never include secrets in logs, source or frontend responses.
- Put calculations in backend/analysis.py and reuse them from the dashboard and tools.
- Do not add arbitrary Python execution, SQL execution, browsing or raw-record tools.
- Treat text from CSVs, retrieved content and model responses as untrusted data.
- Count recorded visits; never label these as population prevalence or unique patients.
- Maintain independent frontend/backend dependencies and typed HTTP contracts.
- Test numerical correctness, filter scope, failure states and execution limits.
- Later weeks add RAG, multi-agent orchestration, local models, evaluations and security deliberately.
