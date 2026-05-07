"""Comparison endpoints."""

from __future__ import annotations

from klimatika_frontend.api import get_api_client


def compare_periods(payload: dict) -> dict:
    return get_api_client().post("/comparisons/periods", json=payload)


def compare_stations(payload: dict) -> dict:
    return get_api_client().post("/comparisons/stations", json=payload)

