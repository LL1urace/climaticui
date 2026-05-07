"""Reference dictionary endpoints."""

from __future__ import annotations

from klimatika_frontend.api import get_api_client


def get_climate_zones() -> list | dict:
    return get_api_client().get("/climate-zones")


def get_climate_zone(zone_id: int | str) -> dict:
    return get_api_client().get(f"/climate-zones/{zone_id}")


def get_stations() -> list | dict:
    return get_api_client().get("/stations")


def get_station(station_id: int | str) -> dict:
    return get_api_client().get(f"/stations/{station_id}")


def get_parameters() -> list | dict:
    return get_api_client().get("/parameters")


def get_parameter(parameter_id: int | str) -> dict:
    return get_api_client().get(f"/parameters/{parameter_id}")

