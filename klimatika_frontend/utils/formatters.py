"""Small formatting and JSON normalization helpers."""

from __future__ import annotations

from collections.abc import Iterable
from datetime import date, datetime
from typing import Any

import pandas as pd


LIST_KEYS = ("items", "data", "results", "values", "records", "stations", "parameters", "climate_zones", "runs")


def unwrap_records(payload: Any, preferred_keys: Iterable[str] = LIST_KEYS) -> list[dict]:
    """Извлекает список словарей из разных форматов backend JSON.

    Args:
        payload: Ответ backend API, список, словарь или None.
        preferred_keys: Ключи, в которых ожидается коллекция записей.

    Returns:
        Список записей-словарей или пустой список.
    """

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
    """Преобразует нормализованный backend JSON в DataFrame.

    Args:
        payload: Ответ backend API или список записей.
        preferred_keys: Ключи, в которых ожидается коллекция записей.

    Returns:
        DataFrame с извлечёнными записями.
    """

    records = unwrap_records(payload, preferred_keys)
    return pd.DataFrame(records)


def get_any(mapping: dict | None, keys: Iterable[str], default: Any = None) -> Any:
    """Возвращает первое непустое значение по набору ключей.

    Args:
        mapping: Словарь для чтения значений.
        keys: Ключи в порядке приоритета.
        default: Значение по умолчанию.

    Returns:
        Найденное значение или default.
    """

    if not isinstance(mapping, dict):
        return default
    for key in keys:
        if key in mapping and mapping[key] not in (None, ""):
            return mapping[key]
    return default


def get_item_id(item: dict, fallback_keys: Iterable[str] = ("id",)) -> Any:
    """Возвращает идентификатор записи по допустимым ключам.

    Args:
        item: Запись справочника или результата backend.
        fallback_keys: Ключи, по которым можно искать идентификатор.

    Returns:
        Идентификатор записи или None.
    """

    return get_any(item, fallback_keys, get_any(item, ("id",)))


def station_id(item: dict) -> Any:
    """Возвращает идентификатор станции из записи backend.

    Args:
        item: Запись метеостанции.

    Returns:
        Значение `id` или `station_id`.
    """

    return get_any(item, ("id", "station_id"))


def parameter_id(item: dict) -> Any:
    """Возвращает идентификатор климатического параметра из записи backend.

    Args:
        item: Запись климатического параметра.

    Returns:
        Значение `id` или `parameter_id`.
    """

    return get_any(item, ("id", "parameter_id"))


def station_label(station: dict) -> str:
    """Формирует человекочитаемую подпись метеостанции.

    Args:
        station: Запись станции из backend API.

    Returns:
        Подпись с названием, кодом, страной и регионом.
    """

    name = get_any(station, ("name", "title"), "Станция")
    code = get_any(station, ("code", "station_code", "wmo_id", "meteostat_id", "id"))
    country = get_any(station, ("country", "country_code"))
    region = get_any(station, ("region", "oblast", "area"))
    code_part = f" ({code})" if code else ""
    place = ", ".join(str(part) for part in (country, region) if part)
    return f"{name}{code_part} - {place}" if place else f"{name}{code_part}"


def parameter_label(parameter: dict) -> str:
    """Формирует человекочитаемую подпись климатического параметра.

    Args:
        parameter: Запись параметра из backend API.

    Returns:
        Подпись с названием и единицей измерения.
    """

    name = get_any(parameter, ("name", "title", "code"), "Параметр")
    unit = get_any(parameter, ("unit", "unit_name", "measure_unit"))
    return f"{name}, {unit}" if unit else str(name)


def format_date(value: Any) -> str:
    """Форматирует дату или дату-время для отображения.

    Args:
        value: Дата, дата-время или произвольное значение.

    Returns:
        Строка даты в ISO-формате или пустая строка для None.
    """

    if isinstance(value, datetime):
        return value.date().isoformat()
    if isinstance(value, date):
        return value.isoformat()
    return str(value) if value is not None else ""


def format_number(value: Any, digits: int = 2) -> str:
    """Форматирует число с фиксированным количеством знаков.

    Args:
        value: Значение, которое нужно отобразить как число.
        digits: Количество знаков после запятой.

    Returns:
        Отформатированная строка или исходное значение в строковом виде.
    """

    try:
        number = float(value)
    except (TypeError, ValueError):
        return "n/a" if value in (None, "") else str(value)
    return f"{number:.{digits}f}"


def format_metric_label(key: str) -> str:
    """Преобразует технический ключ метрики в русскую подпись.

    Args:
        key: Техническое имя метрики из backend JSON.

    Returns:
        Подпись метрики для UI.
    """

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
    """Возвращает вложенный словарь результата анализа из ответа backend.

    Args:
        response: JSON-ответ анализа или сохранённого результата.

    Returns:
        Словарь результатов анализа или пустой словарь.
    """

    if not isinstance(response, dict):
        return {}
    for key in ("results", "result", "result_json"):
        value = response.get(key)
        if isinstance(value, dict):
            return value
    return response


def series_dataframe(payload: Any) -> pd.DataFrame:
    """Нормализует временной ряд backend в DataFrame с колонками date/value.

    Args:
        payload: JSON-ответ временного ряда или список точек.

    Returns:
        DataFrame с переименованными колонками даты и значения.
    """

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

