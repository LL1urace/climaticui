"""Small formatting and JSON normalization helpers."""

from __future__ import annotations

from collections.abc import Iterable
from datetime import date, datetime
from typing import Any

import pandas as pd


LIST_KEYS = ("items", "data", "results", "values", "records", "stations", "parameters", "climate_zones", "runs")


def unwrap_records(payload: Any, preferred_keys: Iterable[str] = LIST_KEYS) -> list[dict]:
    if payload is None:
        return []
    if isinstance(payload, list):
        return [item for item in payload if isinstance(item, dict)]
    if isinstance(payload, dict):
        for key in preferred_keys:
            value = payload.get(key)
            if isinstance(value, list):
                return [item for item in value if isinstance(item, dict)]
            if isinstance(value, dict):
                nested = unwrap_records(value, preferred_keys)
                if nested:
                    return nested
    return []


def to_dataframe(payload: Any, preferred_keys: Iterable[str] = LIST_KEYS) -> pd.DataFrame:
    records = unwrap_records(payload, preferred_keys)
    return pd.DataFrame(records)


def get_any(mapping: dict | None, keys: Iterable[str], default: Any = None) -> Any:
    if not isinstance(mapping, dict):
        return default
    for key in keys:
        if key in mapping and mapping[key] not in (None, ""):
            return mapping[key]
    return default


def get_item_id(item: dict, fallback_keys: Iterable[str] = ("id",)) -> Any:
    return get_any(item, fallback_keys, get_any(item, ("id",)))


def station_id(item: dict) -> Any:
    return get_any(item, ("id", "station_id"))


def parameter_id(item: dict) -> Any:
    return get_any(item, ("id", "parameter_id"))


def station_label(station: dict) -> str:
    name = get_any(station, ("name", "title"), "Станция")
    code = get_any(station, ("code", "station_code", "wmo_id", "meteostat_id", "id"))
    country = get_any(station, ("country", "country_code"))
    region = get_any(station, ("region", "oblast", "area"))
    code_part = f" ({code})" if code else ""
    place = ", ".join(str(part) for part in (country, region) if part)
    return f"{name}{code_part} - {place}" if place else f"{name}{code_part}"


def parameter_label(parameter: dict) -> str:
    name = get_any(parameter, ("name", "title", "code"), "Параметр")
    unit = get_any(parameter, ("unit", "unit_name", "measure_unit"))
    return f"{name}, {unit}" if unit else str(name)


def format_date(value: Any) -> str:
    if isinstance(value, datetime):
        return value.date().isoformat()
    if isinstance(value, date):
        return value.isoformat()
    return str(value) if value is not None else ""


def format_number(value: Any, digits: int = 2) -> str:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return "n/a" if value in (None, "") else str(value)
    return f"{number:.{digits}f}"


def format_metric_label(key: str) -> str:
    labels = {
        "mean": "Среднее",
        "min": "Минимум",
        "max": "Максимум",
        "std": "Стд. отклонение",
        "count": "Наблюдений",
        "sum": "Сумма",
        "median": "Медиана",
        "slope": "Наклон",
        "p_value": "p-value",
        "significant": "Значимость",
        "direction": "Направление",
    }
    return labels.get(key, key.replace("_", " ").capitalize())


def result_payload(response: dict | None) -> dict:
    if not isinstance(response, dict):
        return {}
    for key in ("results", "result", "result_json"):
        value = response.get(key)
        if isinstance(value, dict):
            return value
    return response


def series_dataframe(payload: Any) -> pd.DataFrame:
    records = unwrap_records(payload, ("values", "series", "data", "items", "records"))
    df = pd.DataFrame(records)
    if df.empty:
        return df
    rename = {}
    if "observed_at" in df.columns and "date" not in df.columns:
        rename["observed_at"] = "date"
    if "timestamp" in df.columns and "date" not in df.columns:
        rename["timestamp"] = "date"
    if "y" in df.columns and "value" not in df.columns:
        rename["y"] = "value"
    if rename:
        df = df.rename(columns=rename)
    return df

