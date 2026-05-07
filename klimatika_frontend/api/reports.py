"""Report endpoints."""

from __future__ import annotations

from klimatika_frontend.api import get_api_client


def create_report(analysis_run_id: int | str) -> dict:
    return get_api_client().post("/reports", json={"analysis_run_id": analysis_run_id})


def download_report(report_id: int | str) -> bytes:
    return get_api_client().download(f"/reports/{report_id}/download")
