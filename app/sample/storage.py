"""SQLite storage helpers for sample-mode reference data."""

from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Any


SAMPLE_DATA_DIR = Path(__file__).resolve().parent / "data"
SAMPLE_SQLITE_DB = SAMPLE_DATA_DIR / "klimatika_sample.sqlite"
REAL_MONTHLY_CSV = SAMPLE_DATA_DIR / "arctic_meteostat_monthly_1995_2024.csv"


def _real_monthly_station_ids() -> set[int]:
    """Возвращает ID станций с реальными месячными данными.

    Returns:
        Множество идентификаторов станций из monthly CSV.
    """

    if not REAL_MONTHLY_CSV.exists():
        return set()

    import csv

    with REAL_MONTHLY_CSV.open(encoding="utf-8-sig", newline="") as file:
        return {
            int(row["station_id"])
            for row in csv.DictReader(file)
            if row.get("station_id") and str(row["station_id"]).isdigit()
        }


def _bool(value: Any) -> bool:
    """Преобразует SQLite-значение в bool.

    Args:
        value: Значение из SQLite-строки.

    Returns:
        Логическое значение.
    """

    return bool(value) if value is not None else False


def _station_from_row(row: sqlite3.Row, real_monthly_station_ids: set[int]) -> dict[str, Any]:
    """Преобразует строку таблицы stations в backend-совместимый словарь.

    Args:
        row: SQLite Row из таблицы stations.
        real_monthly_station_ids: ID станций с реальными monthly-данными.

    Returns:
        Словарь станции для sample API.
    """

    station_id = int(row["id"])
    return {
        "id": station_id,
        "code": row["code"],
        "name": row["name"],
        "country": row["country"],
        "region": row["region"],
        "latitude": row["latitude"],
        "longitude": row["longitude"],
        "elevation": row["elevation"],
        "climate_zone_id": row["climate_zone_id"],
        "is_active": _bool(row["is_active"]),
        "source_id": row["source_id"],
        "timezone": row["timezone"],
        "wmo": row["wmo"],
        "icao": row["icao"],
        "iata": row["iata"],
        "temp_start": row["temp_start"],
        "temp_end": row["temp_end"],
        "prcp_start": row["prcp_start"],
        "prcp_end": row["prcp_end"],
        "has_temp": _bool(row["has_temp"]),
        "has_prcp": _bool(row["has_prcp"]),
        "has_rhum": _bool(row["has_rhum"]),
        "has_wspd": _bool(row["has_wspd"]),
        "has_real_monthly_data": station_id in real_monthly_station_ids,
        "data_quality": "real_monthly" if station_id in real_monthly_station_ids else "sample_generated",
    }


def load_stations_from_sqlite(fallback: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Загружает sample-станции из SQLite или возвращает fallback.

    Args:
        fallback: Встроенный список станций на случай отсутствия SQLite.

    Returns:
        Список станций для sample API.
    """

    if not SAMPLE_SQLITE_DB.exists():
        return fallback

    try:
        with sqlite3.connect(SAMPLE_SQLITE_DB) as connection:
            connection.row_factory = sqlite3.Row
            rows = connection.execute(
                """
                SELECT
                    id,
                    source_id,
                    code,
                    name,
                    country,
                    region,
                    latitude,
                    longitude,
                    elevation,
                    climate_zone_id,
                    is_active,
                    timezone,
                    wmo,
                    icao,
                    iata,
                    temp_start,
                    temp_end,
                    prcp_start,
                    prcp_end,
                    has_temp,
                    has_prcp,
                    has_rhum,
                    has_wspd
                FROM stations
                WHERE is_active = 1
                ORDER BY country, name, id
                """
            ).fetchall()
    except sqlite3.Error:
        return fallback

    real_monthly_station_ids = _real_monthly_station_ids()
    stations = [_station_from_row(row, real_monthly_station_ids) for row in rows]
    return stations or fallback
