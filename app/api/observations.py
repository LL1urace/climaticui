"""Observation endpoints."""

from __future__ import annotations

from app.api import get_api_client
from app.api.client import ApiError


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


def get_raw_observations(
    station_id: int | str,
    parameter_id: int | str,
    date_from: str,
    date_to: str,
) -> dict:
    """Получает исходные наблюдения за период без агрегации.

    Args:
        station_id: Идентификатор метеостанции.
        parameter_id: Идентификатор климатического параметра.
        date_from: Начальная дата периода в формате `YYYY-MM-DD`.
        date_to: Конечная дата периода в формате `YYYY-MM-DD`.

    Returns:
        JSON-ответ со строками наблюдений.

    Raises:
        ApiError: Если backend не вернул наблюдения ни через один совместимый endpoint.
    """

    client = get_api_client()
    params = {
        "station_id": station_id,
        "parameter_id": parameter_id,
        "date_from": date_from,
        "date_to": date_to,
    }
    errors = []
    for path in ("/observations", "/observations/raw", "/observations/records"):
        try:
            return client.get(path, params=params)
        except ApiError as error:
            errors.append(error)
            if error.status_code not in {404, 405, 422}:
                break

    try:
        return get_timeseries(station_id, parameter_id, date_from, date_to, "raw")
    except ApiError as error:
        errors.append(error)
        raise errors[-1]


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

