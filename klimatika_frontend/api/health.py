"""Fast health check helpers."""

from __future__ import annotations

from klimatika_frontend.api.client import ApiClient
from klimatika_frontend.config import get_settings


def get_health(timeout: float = 0.75) -> dict:
    settings = get_settings()
    return ApiClient(settings.backend_api_url, timeout=timeout).get("/health")
