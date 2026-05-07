"""Observation endpoints."""

from __future__ import annotations

from klimatika_frontend.api import get_api_client


def get_timeseries(
    station_id: int | str,
    parameter_id: int | str,
    date_from: str,
    date_to: str,
    aggregation: str,
) -> dict:
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
    return get_api_client().get(
        "/observations/availability",
        params={"station_id": station_id, "parameter_id": parameter_id},
    )

