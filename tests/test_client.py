"""The real frontend HTTP boundary: backend errors become clear user messages."""

import httpx
import pytest

from frontend import client

REQUEST = httpx.Request("GET", "http://backend/x")


def respond(monkeypatch, response=None, error=None):
    calls = []

    def fake_request(method, url, **kwargs):
        calls.append((method, url, kwargs))
        if error:
            raise error
        return response

    monkeypatch.setattr(client.httpx, "request", fake_request)
    return calls


def test_success_uses_backend_url_and_timeout(monkeypatch):
    monkeypatch.setenv("BACKEND_URL", "http://api.test:9000/")
    calls = respond(monkeypatch, httpx.Response(200, json={"status": "ok"}, request=REQUEST))
    assert client.api("GET", "/health") == {"status": "ok"}
    method, url, kwargs = calls[0]
    assert (method, url) == ("GET", "http://api.test:9000/health")
    assert kwargs["timeout"] == client.HTTP_TIMEOUT_S


def test_empty_response_returns_none(monkeypatch):
    respond(monkeypatch, httpx.Response(204, request=REQUEST))
    assert client.api("DELETE", "/datasets/x") is None


@pytest.mark.parametrize(
    "response,status,message",
    [
        (httpx.Response(404, json={"detail": "Dataset expired."}, request=REQUEST), 404, "Dataset expired."),
        (
            httpx.Response(
                422,
                json={"detail": {"message": "CSV validation failed.", "issues": ["a", "b"]}},
                request=REQUEST,
            ),
            422,
            "a\nb",
        ),
        (
            httpx.Response(422, json={"detail": [{"loc": ["body"]}]}, request=REQUEST),
            422,
            "check the selected",
        ),
        (httpx.Response(500, text="<html>oops</html>", request=REQUEST), 500, "could not be completed"),
    ],
    ids=["string-detail", "csv-issues", "pydantic-errors", "non-json"],
)
def test_error_details_become_readable_messages(monkeypatch, response, status, message):
    respond(monkeypatch, response)
    with pytest.raises(client.ApiError) as exc:
        client.api("POST", "/x")
    assert exc.value.status_code == status
    assert message in str(exc.value)
    assert "<html>" not in str(exc.value)


@pytest.mark.parametrize(
    "error,status,message",
    [
        (httpx.ReadTimeout("slow", request=REQUEST), 504, "took too long"),
        (httpx.ConnectError("refused", request=REQUEST), 503, "Cannot reach the backend"),
    ],
)
def test_network_failures(monkeypatch, error, status, message):
    respond(monkeypatch, error=error)
    with pytest.raises(client.ApiError) as exc:
        client.api("GET", "/health")
    assert exc.value.status_code == status
    assert message in str(exc.value)
