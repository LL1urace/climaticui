"""Saved analysis set endpoints."""

from __future__ import annotations

from app.api import get_api_client


def create_saved_analysis_set(payload: dict) -> dict:
    """Сохраняет пользовательский набор анализа через backend API.

    Args:
        payload: JSON-тело сохранённого набора анализа.

    Returns:
        JSON-ответ с созданной записью набора.

    Raises:
        ApiError: Если backend вернул ошибку или недоступен.
    """

    return get_api_client().post("/saved-analysis-sets", json=payload)


def get_saved_analysis_sets() -> list | dict:
    """Получает сохранённые наборы анализа текущего пользователя.

    Returns:
        JSON-ответ со списком сохранённых наборов анализа.

    Raises:
        ApiError: Если backend вернул ошибку или недоступен.
    """

    return get_api_client().get("/saved-analysis-sets")

