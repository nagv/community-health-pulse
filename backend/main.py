"""Run with: python -m uvicorn backend.main:app --port 8000 (repository root)."""

import hmac
import logging
import os
from pathlib import Path
from typing import Annotated

from fastapi import Depends, FastAPI, File, Header, HTTPException, Response, UploadFile

from backend.agent import AgentFailure, configured, run_chat
from backend.data import MAX_BYTES, DatasetStore, InvalidDataset, sample_csv
from shared.models import (
    ChartSpec,
    ChatRequest,
    ChatResponse,
    DashboardRequest,
    DashboardResponse,
    DatasetInfo,
    Filters,
    Summary,
)

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s %(message)s")
store = DatasetStore()
app = FastAPI(title="Community Health Pulse API", version="0.1.0")


def require_token(x_api_token: Annotated[str | None, Header()] = None):
    """When BACKEND_API_TOKEN is set (any public deployment), every data route requires it."""
    expected = os.getenv("BACKEND_API_TOKEN", "")
    if expected and not hmac.compare_digest((x_api_token or "").encode(), expected.encode()):
        raise HTTPException(401, "Missing or invalid API token.")


protected = [Depends(require_token)]


def get_dataset(dataset_id: str):
    try:
        return store.get(dataset_id)
    except KeyError:
        raise HTTPException(404, "Dataset expired or is unavailable. Load or upload it again.") from None


@app.get("/health")
def health():
    return {"status": "ok", "agent_configured": configured(), "storage": "in-memory"}


@app.post("/datasets", response_model=DatasetInfo, status_code=201, dependencies=protected)
async def upload(file: Annotated[UploadFile, File()]):
    try:
        payload = await file.read(MAX_BYTES + 1)
        return store.add(payload, Path(file.filename or "uploaded.csv").name)
    except InvalidDataset as exc:
        raise HTTPException(422, {"message": str(exc), "issues": exc.issues}) from None
    finally:
        await file.close()


@app.post("/datasets/sample", response_model=DatasetInfo, status_code=201, dependencies=protected)
def load_sample():
    return store.add(sample_csv(), "Synthetic clinic visits — 90 days", synthetic=True)


@app.get("/datasets/{dataset_id}", response_model=DatasetInfo, dependencies=protected)
def metadata(dataset_id: str):
    return get_dataset(dataset_id).info


@app.delete("/datasets/{dataset_id}", status_code=204, dependencies=protected)
def delete_dataset(dataset_id: str):
    store.delete(dataset_id)
    return Response(status_code=204)


@app.post("/datasets/{dataset_id}/analysis", response_model=DashboardResponse, dependencies=protected)
def dashboard(dataset_id: str, request: DashboardRequest):
    analysis = get_dataset(dataset_id).analysis
    f = request.filters
    all_conditions = analysis.breakdown(f, "condition")
    conditions = all_conditions[:50]
    trend = analysis.trend(f, "weekly")
    all_localities = analysis.breakdown(f, "locality")
    localities = all_localities[:50]
    charts = [
        ChartSpec(
            result_id="dashboard-trend",
            title="Visits over time",
            kind="line",
            x="period",
            y="visits",
            rows=trend,
            filters=f.model_dump(mode="json"),
        ),
        ChartSpec(
            result_id="dashboard-conditions",
            title="Top recorded conditions",
            kind="bar",
            x="condition",
            y="visits",
            rows=conditions,
            truncated=len(all_conditions) > 50,
            total_groups=len(all_conditions),
            filters=f.model_dump(mode="json"),
        ),
        ChartSpec(
            result_id="dashboard-localities",
            title="Visits by locality",
            kind="bar",
            x="locality",
            y="visits",
            rows=localities,
            truncated=len(all_localities) > 50,
            total_groups=len(all_localities),
            filters=f.model_dump(mode="json"),
        ),
    ]
    return DashboardResponse(
        condition_groups=len(all_conditions),
        summary=analysis.summary(f),
        filters=f,
        charts=charts,
        conditions=conditions,
        records=analysis.records(f, request.page, request.page_size),
    )


@app.post("/datasets/{dataset_id}/summary", response_model=Summary, dependencies=protected)
def summary(dataset_id: str, filters: Filters):
    """Headline numbers only: cheaper than /analysis for views that don't need charts or records."""
    return get_dataset(dataset_id).analysis.summary(filters)


@app.post("/chat", response_model=ChatResponse, dependencies=protected)
async def chat(request: ChatRequest):
    analysis = get_dataset(request.dataset_id).analysis
    try:
        return await run_chat(analysis, request)
    except AgentFailure as exc:
        raise HTTPException(exc.status_code, str(exc)) from None
