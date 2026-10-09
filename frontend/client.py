"""Small HTTP boundary; no model keys or analysis calculations in the frontend."""

import os
from pathlib import Path

import httpx
from dotenv import load_dotenv

load_dotenv(Path(__file__).with_name(".env"))


class ApiError(Exception):
    def __init__(self, message, status_code=502):
        self.status_code = status_code
        super().__init__(message)


def api(method: str, path: str, **kwargs):
    base = os.getenv("BACKEND_URL", "http://127.0.0.1:8000").rstrip("/")
    try:
        response = httpx.request(method, base + path, timeout=65, **kwargs)
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
