"""Observation endpoints."""

from __future__ import annotations

from app.api import get_api_client


def get_timeseries(
    station_id: int | str,
    parameter_id: int | str,
    date_from: str,
    date_to: str,
    aggregation: str,
) -> dict:
    """Получает временной ряд наблюдений через backend API.

    Args:
        station_id: Идентификатор метеостанции.
        parameter_id: Идентификатор климатического параметра.
        date_from: Начальная дата периода в формате `YYYY-MM-DD`.
        date_to: Конечная дата периода в формате `YYYY-MM-DD`.
        aggregation: Тип агрегации: `raw`, `monthly` или `yearly`.

    Returns:
        JSON-ответ со значениями временного ряда.

    Raises:
        ApiError: Если наблюдения не найдены или backend вернул ошибку.
    """

    return get_api_client().get(
        "/observations/timeseries",
        params={
            "station_id": station_id,
            "parameter_id": parameter_id,
            "date_from": date_from,
            "date_to": date_to,
            "aggregation": aggregation,
        },
    )


def get_availability(station_id: int | str, parameter_id: int | str) -> dict:
    """Получает доступный период наблюдений для станции и параметра.

    Args:
        station_id: Идентификатор метеостанции.
        parameter_id: Идентификатор климатического параметра.

    Returns:
        JSON-ответ с датами доступности и количеством наблюдений.

    Raises:
        ApiError: Если backend вернул ошибку доступности.
    """

    return get_api_client().get(
        "/observations/availability",
        params={"station_id": station_id, "parameter_id": parameter_id},
    )

