"""Small HTTP boundary; no model keys or analysis calculations in the frontend."""

import json
import os
import time
from pathlib import Path

import httpx
import streamlit as st
from dotenv import load_dotenv

load_dotenv(Path(__file__).with_name(".env"))

# Slightly longer than the backend's 60-second agent deadline so its own timeout message wins.
HTTP_TIMEOUT_S = 65
HEALTH_TTL_S = 30


class ApiError(Exception):
    def __init__(self, message, status_code=502):
        self.status_code = status_code
        super().__init__(message)


def api(method: str, path: str, **kwargs):
    base = os.getenv("BACKEND_URL", "http://127.0.0.1:8000").rstrip("/")
    token = os.getenv("BACKEND_API_TOKEN")
    headers = {"X-API-Token": token} if token else None
    try:
        response = httpx.request(method, base + path, headers=headers, timeout=HTTP_TIMEOUT_S, **kwargs)
    except httpx.TimeoutException:
        raise ApiError("The backend took too long to respond. Please try again.", 504) from None
    except httpx.RequestError:
        raise ApiError("Cannot reach the backend. Start the API service and try again.", 503) from None
    if response.is_error:
        try:
            detail = response.json().get("detail", "The request could not be completed.")
        except ValueError:
            detail = "The request could not be completed."
        if isinstance(detail, dict):
            detail = "\n".join(detail.get("issues", [detail.get("message", "Invalid CSV.")]))
        elif isinstance(detail, list):
            detail = "Please check the selected filters and request fields."
        raise ApiError(str(detail), response.status_code)
    return response.json() if response.content else None


# The helpers below call `api` through the module global so tests can monkeypatch it.


def health() -> dict:
    """Backend health, re-checked at most every HEALTH_TTL_S seconds per browser session."""
    cached = st.session_state.get("_health")
    if cached and time.monotonic() - cached[0] < HEALTH_TTL_S:
        return cached[1]
    result = api("GET", "/health")
    st.session_state["_health"] = (time.monotonic(), result)
    return result


@st.cache_data(ttl=300, show_spinner=False)
def _dashboard(dataset_id: str, filters_json: str, page: int) -> dict:
    return api(
        "POST",
        f"/datasets/{dataset_id}/analysis",
        json={"filters": json.loads(filters_json), "page": page, "page_size": 25},
    )


@st.cache_data(ttl=300, show_spinner=False)
def _summary(dataset_id: str, filters_json: str) -> dict:
    return api("POST", f"/datasets/{dataset_id}/summary", json=json.loads(filters_json))


def dashboard(dataset_id: str, filters: dict, page: int) -> dict:
    """Charts, summary and one records page. Cached per dataset, filters and page."""
    return _dashboard(dataset_id, json.dumps(filters, sort_keys=True), page)


def summary(dataset_id: str, filters: dict) -> dict:
    """Headline numbers only (cheaper than dashboard). Cached per dataset and filters."""
    return _summary(dataset_id, json.dumps(filters, sort_keys=True))


def clear_caches() -> None:
    _dashboard.clear()
    _summary.clear()
    st.session_state.pop("_health", None)
