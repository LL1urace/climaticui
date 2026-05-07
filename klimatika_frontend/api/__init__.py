"""API wrapper factory."""

from __future__ import annotations

from klimatika_frontend.api.client import ApiClient
from klimatika_frontend.config import get_settings
from klimatika_frontend.state.session import clear_auth_state, get_access_token


def get_api_client() -> ApiClient:
    settings = get_settings()
    return ApiClient(
        base_url=settings.backend_api_url,
        token=get_access_token(),
        timeout=settings.request_timeout_seconds,
        on_unauthorized=clear_auth_state,
    )

