"""Forecast endpoints."""

from __future__ import annotations

from klimatika_frontend.api import get_api_client


def run_forecast(payload: dict) -> dict:
    return get_api_client().post("/forecasts/run", json=payload)

