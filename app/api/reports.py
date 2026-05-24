"""Report endpoints."""

from __future__ import annotations

from app.api import get_api_client


def create_report(analysis_run_id: int | str) -> dict:
    """Создаёт отчёт по результату анализа через backend API.

    Args:
        analysis_run_id: Идентификатор запуска анализа.

    Returns:
        JSON-ответ с метаданными созданного отчёта.

    Raises:
        ApiError: Если backend не смог создать отчёт.
    """

    return get_api_client().post("/reports", json={"analysis_run_id": analysis_run_id})


def download_report(report_id: int | str) -> bytes:
    """Скачивает содержимое отчёта через backend API.

    Args:
        report_id: Идентификатор отчёта.

    Returns:
        Байты файла отчёта.

    Raises:
        ApiError: Если отчёт не найден или backend вернул ошибку.
    """

    return get_api_client().download(f"/reports/{report_id}/download")
