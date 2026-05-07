"""Analysis endpoints."""

from __future__ import annotations

from klimatika_frontend.api import get_api_client


def run_analysis(payload: dict) -> dict:
    return get_api_client().post("/analysis/run", json=payload)


def get_history() -> list | dict:
    return get_api_client().get("/analysis/history")


def get_analysis_result(analysis_run_id: int | str) -> dict:
    return get_api_client().get(f"/analysis/{analysis_run_id}")


def run_correlation(payload: dict) -> dict:
    return get_api_client().post("/analysis/correlation", json=payload)


def run_climatogram(payload: dict) -> dict:
    return get_api_client().post("/analysis/climatogram", json=payload)

