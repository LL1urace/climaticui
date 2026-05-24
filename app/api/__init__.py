"""API wrapper factory."""

from __future__ import annotations

from app.api.client import ApiClient
from app.config import get_settings
from app.state.session import clear_auth_state, get_access_token


def get_api_client():
    """Создаёт API-клиент для backend или локального sample-режима.

    Returns:
        Клиент с методами `get`, `post` и `download`.
    """

    settings = get_settings()
    if settings.use_sample_data:
        from app.sample.client import SampleApiClient

        return SampleApiClient(token=get_access_token())
    return ApiClient(
        base_url=settings.backend_api_url,
        token=get_access_token(),
        timeout=settings.request_timeout_seconds,
        on_unauthorized=clear_auth_state,
    )

