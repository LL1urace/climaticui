"""Analysis endpoints."""

from __future__ import annotations

from app.api import get_api_client


def run_analysis(payload: dict) -> dict:
    """Запускает анализ временного ряда через backend API.

    Args:
        payload: JSON-тело запроса анализа.

    Returns:
        JSON-ответ с идентификатором запуска и результатами анализа.

    Raises:
        ApiError: Если backend вернул ошибку или недоступен.
    """

    return get_api_client().post("/analysis/run", json=payload)


def get_history() -> list | dict:
    """Получает историю анализов текущего пользователя.

    Returns:
        JSON-ответ со списком запусков анализа.

    Raises:
        ApiError: Если backend вернул ошибку или недоступен.
    """

    return get_api_client().get("/analysis/history")


def get_analysis_result(analysis_run_id: int | str) -> dict:
    """Получает сохранённый результат анализа по идентификатору.

    Args:
        analysis_run_id: Идентификатор запуска анализа.

    Returns:
        JSON-ответ с параметрами запуска и результатом.

    Raises:
        ApiError: Если результат не найден или backend вернул ошибку.
    """

    return get_api_client().get(f"/analysis/{analysis_run_id}")


def run_correlation(payload: dict) -> dict:
    """Запускает корреляционный анализ через backend API.

    Args:
        payload: JSON-тело запроса корреляции.

    Returns:
        JSON-ответ с коэффициентом корреляции и метаданными.

    Raises:
        ApiError: Если backend вернул ошибку или недоступен.
    """

    return get_api_client().post("/analysis/correlation", json=payload)


def run_climatogram(payload: dict) -> dict:
    """Запрашивает построение климатограммы через backend API.

    Args:
        payload: JSON-тело запроса климатограммы.

    Returns:
        JSON-ответ с месячными значениями температуры и осадков.

    Raises:
        ApiError: Если backend вернул ошибку или недоступен.
    """

    return get_api_client().post("/analysis/climatogram", json=payload)

