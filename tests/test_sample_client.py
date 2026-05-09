from __future__ import annotations

import json

from klimatika_frontend.sample.client import SampleApiClient


def test_sample_client_runs_full_analysis_and_report() -> None:
    """Проверяет полный sample-сценарий анализа и скачивания отчёта.

    Returns:
        None.
    """

    client = SampleApiClient(token="sample")
    stations = client.get("/stations")["items"]
    parameters = client.get("/parameters")["items"]
    assert stations
    assert parameters

    payload = {
        "station_id": stations[0]["id"],
        "parameter_id": parameters[0]["id"],
        "date_from": "2020-01-01",
        "date_to": "2024-12-01",
        "aggregation": "monthly",
        "methods": ["basic_statistics", "moving_average", "linear_trend", "climate_norm", "anomalies"],
        "options": {"moving_average_window": 12},
    }
    result = client.post("/analysis/run", json=payload)
    assert result["status"] == "completed"
    assert "basic_statistics" in result["results"]

    history = client.get("/analysis/history")["items"]
    assert history[0]["analysis_run_id"] == result["analysis_run_id"]

    report = client.post("/reports", json={"analysis_run_id": result["analysis_run_id"]})
    content = json.loads(client.download(f"/reports/{report['report_id']}/download").decode("utf-8"))
    assert content["analysis_run_id"] == result["analysis_run_id"]
