"""Reference dictionary endpoints."""

from __future__ import annotations

from klimatika_frontend.api import get_api_client


def get_climate_zones() -> list | dict:
    """Получает список климатических зон из backend API.

    Returns:
        JSON-ответ со списком климатических зон.

    Raises:
        ApiError: Если backend вернул ошибку или недоступен.
    """

    return get_api_client().get("/climate-zones")


def get_climate_zone(zone_id: int | str) -> dict:
    """Получает климатическую зону по идентификатору.

    Args:
        zone_id: Идентификатор климатической зоны.

    Returns:
        JSON-ответ с данными климатической зоны.

    Raises:
        ApiError: Если зона не найдена или backend вернул ошибку.
    """

    return get_api_client().get(f"/climate-zones/{zone_id}")


def get_stations() -> list | dict:
    """Получает список метеостанций из backend API.

    Returns:
        JSON-ответ со списком метеостанций.

    Raises:
        ApiError: Если backend вернул ошибку или недоступен.
    """

    return get_api_client().get("/stations")


def get_station(station_id: int | str) -> dict:
    """Получает метеостанцию по идентификатору.

    Args:
        station_id: Идентификатор метеостанции.

    Returns:
        JSON-ответ с данными метеостанции.

    Raises:
        ApiError: Если станция не найдена или backend вернул ошибку.
    """

    return get_api_client().get(f"/stations/{station_id}")


def get_parameters() -> list | dict:
    """Получает список климатических параметров из backend API.

    Returns:
        JSON-ответ со списком климатических параметров.

    Raises:
        ApiError: Если backend вернул ошибку или недоступен.
    """

    return get_api_client().get("/parameters")


def get_parameter(parameter_id: int | str) -> dict:
    """Получает климатический параметр по идентификатору.

    Args:
        parameter_id: Идентификатор климатического параметра.

    Returns:
        JSON-ответ с данными параметра.

    Raises:
        ApiError: Если параметр не найден или backend вернул ошибку.
    """

    return get_api_client().get(f"/parameters/{parameter_id}")

