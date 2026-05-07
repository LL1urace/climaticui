from __future__ import annotations

import httpx
import pytest

from klimatika_frontend.api.client import ApiClient, ApiError


def make_client(handler, token: str | None = "token") -> ApiClient:
    return ApiClient("http://backend/api/v1", token=token, timeout=1, transport=httpx.MockTransport(handler))


def test_api_client_adds_bearer_token() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.headers["Authorization"] == "Bearer token"
        return httpx.Response(200, json={"status": "ok"})

    assert make_client(handler).get("/health") == {"status": "ok"}


def test_api_client_parses_backend_detail_error() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            400,
            json={"detail": {"code": "NOT_ENOUGH_DATA", "message": "Недостаточно данных", "context": {"count": 3}}},
        )

    with pytest.raises(ApiError) as exc:
        make_client(handler).get("/analysis/history")
    assert exc.value.code == "NOT_ENOUGH_DATA"
    assert exc.value.message == "Недостаточно данных"
    assert exc.value.context == {"count": 3}


def test_api_client_calls_unauthorized_callback() -> None:
    called = {"value": False}

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(401, json={"detail": {"code": "UNAUTHORIZED", "message": "Login required"}})

    client = ApiClient(
        "http://backend/api/v1",
        token="expired",
        transport=httpx.MockTransport(handler),
        on_unauthorized=lambda: called.__setitem__("value", True),
    )

    with pytest.raises(ApiError):
        client.get("/users/me")
    assert called["value"] is True


def test_api_client_handles_non_json_error() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(500, text="boom")

    with pytest.raises(ApiError) as exc:
        make_client(handler).get("/health")
    assert exc.value.code == "HTTP_500"


def test_api_client_download_returns_bytes() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, content=b"file-content")

    assert make_client(handler).download("/reports/1/download") == b"file-content"

