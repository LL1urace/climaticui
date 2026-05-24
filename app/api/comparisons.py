"""Comparison endpoints."""

from __future__ import annotations

from app.api import get_api_client


def compare_periods(payload: dict) -> dict:
    """Сравнивает два периода через backend API.

    Args:
        payload: JSON-тело с параметрами станции, параметра и периодов.

    Returns:
        JSON-ответ со статистикой и разницей периодов.

    Raises:
        ApiError: Если backend отклонил запрос сравнения.
    """

    return get_api_client().post("/comparisons/periods", json=payload)


def compare_stations(payload: dict) -> dict:
    """Сравнивает несколько станций через backend API.

    Args:
        payload: JSON-тело с выбранными станциями, периодом и метрикой.

    Returns:
        JSON-ответ с результатами сравнения станций.

    Raises:
        ApiError: Если backend отклонил запрос сравнения.
    """

    return get_api_client().post("/comparisons/stations", json=payload)

