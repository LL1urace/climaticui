"""Local downloaded observation slices used for raw CSV export."""

from __future__ import annotations

import csv
import gzip
from datetime import date
from functools import lru_cache
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[2]
LOCAL_MONTHLY_CSV = PROJECT_ROOT / "app" / "sample" / "data" / "arctic_meteostat_monthly_1995_2024.csv"
LOCAL_BULK_DIR = PROJECT_ROOT / "app" / "sample" / "data" / "meteostat_arctic_20_daily_monthly"

PARAMETER_VALUE_COLUMNS = {
    1: ("tavg", "temp"),
    2: ("prcp",),
    3: ("rhum", "humidity"),
    4: ("pres",),
}
PARAMETER_SOURCE_COLUMNS = {
    1: ("tavg_source", "temp_source"),
    2: ("prcp_source",),
    3: ("rhum_source", "humidity_source"),
    4: ("pres_source",),
}


def _parse_date(value: Any) -> date | None:
    """Parses ISO date-like values from local CSV rows."""

    if isinstance(value, date):
        return value
    if isinstance(value, str) and value:
        try:
            return date.fromisoformat(value[:10])
        except ValueError:
            return None
    return None


def _parameter_id(value: Any) -> int | None:
    """Normalizes parameter id values."""

    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _first_present(row: dict[str, str], columns: tuple[str, ...]) -> tuple[str | None, str | None]:
    """Returns the first non-empty cell and its column name."""

    for column in columns:
        value = row.get(column)
        if value not in (None, ""):
            return column, value
    return None, None


@lru_cache(maxsize=512)
def _csv_rows(path: Path) -> tuple[dict[str, str], ...]:
    """Loads a plain CSV or gzip-compressed CSV file."""

    if not path.exists():
        return ()
    opener = gzip.open if path.suffix == ".gz" else open
    with opener(path, mode="rt", encoding="utf-8-sig", newline="") as file:
        return tuple(csv.DictReader(file))


def _date_from_parts(row: dict[str, str], day_default: int = 1) -> date | None:
    """Builds a date from Meteostat year/month/day columns."""

    try:
        year = int(row.get("year") or "")
        month = int(row.get("month") or "")
        day = int(row.get("day") or day_default)
    except ValueError:
        return None
    try:
        return date(year, month, day)
    except ValueError:
        return None


def _row_date(row: dict[str, str], day_default: int = 1) -> date | None:
    """Returns a row observation date from supported local CSV schemas."""

    observed = _parse_date(row.get("date") or row.get("observed_at") or row.get("time"))
    return observed or _date_from_parts(row, day_default=day_default)


def _source_ref(path: Path, row: dict[str, str]) -> str:
    """Returns a readable reference to the local downloaded source file."""

    explicit_source = row.get("monthly_url") or row.get("source_url")
    if explicit_source:
        return explicit_source
    try:
        return f"local://{path.relative_to(PROJECT_ROOT).as_posix()}"
    except ValueError:
        return f"local://{path.as_posix()}"


def _station_matches(row: dict[str, str], station_key: str) -> bool:
    """Checks a row station id when the CSV schema contains it."""

    row_station = row.get("station_id") or row.get("wmo") or row.get("code")
    return not row_station or str(row_station) == station_key


def _station_files(station_key: str, granularity: str, start: date, end: date) -> list[Path]:
    """Returns candidate local files for a station and granularity."""

    base = LOCAL_BULK_DIR / granularity
    if granularity == "daily":
        files = []
        for year in range(start.year, end.year + 1):
            year_dir = base / str(year)
            files.extend([year_dir / f"{station_key}.csv.gz", year_dir / f"{station_key}.csv"])
        return [path for path in files if path.exists()]
    return [path for path in (base / f"{station_key}.csv.gz", base / f"{station_key}.csv") if path.exists()]


def _rows_from_files(
    files: list[Path],
    station_key: str,
    pid: int,
    start: date,
    end: date,
    source_name: str,
    day_default: int = 1,
) -> list[dict[str, Any]]:
    """Extracts station/parameter/date rows from local Meteostat files."""

    rows: list[dict[str, Any]] = []
    for path in files:
        for row in _csv_rows(path):
            if not _station_matches(row, station_key):
                continue
            observed = _row_date(row, day_default=day_default)
            if observed is None or observed < start or observed > end:
                continue

            value_column, value = _first_present(row, PARAMETER_VALUE_COLUMNS[pid])
            if value is None:
                continue
            source_column, quality_flag = _first_present(row, PARAMETER_SOURCE_COLUMNS.get(pid, ()))
            rows.append(
                {
                    "station_id": row.get("station_id") or row.get("wmo") or station_key,
                    "station_name": row.get("station_name"),
                    "parameter_id": pid,
                    "date": observed.isoformat(),
                    "observed_at": observed.isoformat(),
                    "value": value,
                    "value_column": value_column,
                    "quality_flag": quality_flag,
                    "quality_column": source_column,
                    "source_name": source_name,
                    "source_url": _source_ref(path, row),
                }
            )
    return rows


def local_raw_observation_rows(
    station_id: int | str,
    parameter_id: int | str,
    date_from: str,
    date_to: str,
) -> list[dict[str, Any]]:
    """Returns downloaded local rows for a station/parameter/date slice.

    Daily Meteostat files from the 20-station demo pack are used first. If a
    daily slice is unavailable, the function falls back to monthly downloaded
    rows and finally to the old consolidated 9-station CSV.
    """

    pid = _parameter_id(parameter_id)
    if pid not in PARAMETER_VALUE_COLUMNS:
        return []

    start = _parse_date(date_from)
    end = _parse_date(date_to)
    if start is None or end is None:
        return []

    station_key = str(station_id)
    rows = _rows_from_files(
        _station_files(station_key, "daily", start, end),
        station_key,
        pid,
        start,
        end,
        "local_meteostat_daily_csv_gz",
        day_default=1,
    )
    if not rows:
        rows = _rows_from_files(
            _station_files(station_key, "monthly", start, end),
            station_key,
            pid,
            start,
            end,
            "local_meteostat_monthly_csv_gz",
            day_default=1,
        )
    if not rows:
        rows = _rows_from_files(
            [LOCAL_MONTHLY_CSV],
            station_key,
            pid,
            start,
            end,
            "local_meteostat_monthly_csv",
            day_default=1,
        )
    return sorted(rows, key=lambda item: item["date"])
