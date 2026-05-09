"""Fast health check helpers."""

from __future__ import annotations

from klimatika_frontend.api.client import ApiClient
from klimatika_frontend.config import get_settings
from klimatika_frontend.sample.client import SampleApiClient


def get_health(timeout: float = 0.75) -> dict:
    """Проверяет доступность backend API или sample-режима.

    Args:
        timeout: Таймаут health-запроса в секундах.

    Returns:
        JSON-ответ статуса сервиса.

    Raises:
        ApiError: Если backend недоступен или вернул ошибку.
    """

    settings = get_settings()
    if settings.use_sample_data:
        return SampleApiClient().get("/health")
    return ApiClient(settings.backend_api_url, timeout=timeout).get("/health")
