"""Forecast endpoints."""

from __future__ import annotations

from klimatika_frontend.api import get_api_client


def run_forecast(payload: dict) -> dict:
    """Запускает прогнозирование через backend API.

    Args:
        payload: JSON-тело с параметрами прогноза.

    Returns:
        JSON-ответ с прогнозными значениями.

    Raises:
        ApiError: Если backend вернул ошибку прогноза.
    """

    return get_api_client().post("/forecasts/run", json=payload)

