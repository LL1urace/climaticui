"""Deterministic sample data shaped after the backend ORM models."""

from __future__ import annotations

import csv
from datetime import date, datetime
import math
from pathlib import Path


SAMPLE_USER = {
    "id": 1,
    "email": "demo@klimatika.local",
    "full_name": "Демо исследователь",
    "is_active": True,
    "created_at": "2026-01-01T00:00:00+00:00",
    "updated_at": "2026-01-01T00:00:00+00:00",
}


CLIMATE_ZONES = [
    {
        "id": 1,
        "code": "Dfb",
        "name": "Влажный континентальный климат",
        "description": "Холодная зима, тёплое лето, осадки круглый год.",
    },
    {
        "id": 2,
        "code": "Dfa",
        "name": "Континентальный климат с жарким летом",
        "description": "Выраженная сезонность и жаркое лето.",
    },
    {
        "id": 3,
        "code": "Cfa",
        "name": "Влажный субтропический климат",
        "description": "Мягкая зима, влажное лето.",
    },
    {
        "id": 4,
        "code": "Arctic",
        "name": "Арктический климат",
        "description": "Очень холодная зима, короткое прохладное лето и выраженная сезонность.",
    },
]


STATIONS = [
    {
        "id": 1,
        "code": "27612",
        "name": "Moscow VDNKh",
        "country": "RU",
        "region": "Central",
        "latitude": 55.8263,
        "longitude": 37.6365,
        "elevation": 150.0,
        "climate_zone_id": 1,
        "is_active": True,
    },
    {
        "id": 2,
        "code": "36870",
        "name": "Almaty",
        "country": "KZ",
        "region": "Almaty",
        "latitude": 43.2567,
        "longitude": 76.9286,
        "elevation": 760.0,
        "climate_zone_id": 2,
        "is_active": True,
    },
    {
        "id": 3,
        "code": "54511",
        "name": "Beijing",
        "country": "CN",
        "region": "Beijing",
        "latitude": 39.9042,
        "longitude": 116.4074,
        "elevation": 43.0,
        "climate_zone_id": 2,
        "is_active": True,
    },
    {
        "id": 4,
        "code": "47662",
        "name": "Tokyo",
        "country": "JP",
        "region": "Kanto",
        "latitude": 35.6762,
        "longitude": 139.6503,
        "elevation": 40.0,
        "climate_zone_id": 3,
        "is_active": True,
    },
    {
        "id": 20674,
        "code": "20674",
        "name": "Ostrov Dikson",
        "country": "RU",
        "region": "TAY",
        "latitude": 73.5,
        "longitude": 80.4,
        "elevation": 47.0,
        "climate_zone_id": 4,
        "is_active": True,
    },
    {
        "id": 21824,
        "code": "21824",
        "name": "Tiksi",
        "country": "RU",
        "region": "SA",
        "latitude": 71.5833,
        "longitude": 128.9167,
        "elevation": 8.0,
        "climate_zone_id": 4,
        "is_active": True,
    },
    {
        "id": 21921,
        "code": "21921",
        "name": "Kjusjur",
        "country": "RU",
        "region": "SA",
        "latitude": 70.6833,
        "longitude": 127.4,
        "elevation": 39.0,
        "climate_zone_id": 4,
        "is_active": True,
    },
    {
        "id": 23022,
        "code": "23022",
        "name": "Amderma",
        "country": "RU",
        "region": "NEN",
        "latitude": 69.75,
        "longitude": 61.7,
        "elevation": 53.0,
        "climate_zone_id": 4,
        "is_active": True,
    },
    {
        "id": 23078,
        "code": "23078",
        "name": "Norilsk",
        "country": "RU",
        "region": "TAY",
        "latitude": 69.3333,
        "longitude": 88.1,
        "elevation": 62.0,
        "climate_zone_id": 4,
        "is_active": True,
    },
    {
        "id": 22113,
        "code": "22113",
        "name": "Murmansk",
        "country": "RU",
        "region": "MUR",
        "latitude": 68.9667,
        "longitude": 33.05,
        "elevation": 51.0,
        "climate_zone_id": 4,
        "is_active": True,
    },
    {
        "id": 23205,
        "code": "23205",
        "name": "Nar'Jan-Mar",
        "country": "RU",
        "region": "NN",
        "latitude": 67.6333,
        "longitude": 53.0333,
        "elevation": 7.0,
        "climate_zone_id": 4,
        "is_active": True,
    },
    {
        "id": 23226,
        "code": "23226",
        "name": "Vorkuta",
        "country": "RU",
        "region": "KO",
        "latitude": 67.4833,
        "longitude": 64.0167,
        "elevation": 180.0,
        "climate_zone_id": 4,
        "is_active": True,
    },
    {
        "id": 22217,
        "code": "22217",
        "name": "Kandalaksa",
        "country": "RU",
        "region": "MUR",
        "latitude": 67.15,
        "longitude": 32.35,
        "elevation": 26.0,
        "climate_zone_id": 4,
        "is_active": True,
    },
    {
        "id": 23330,
        "code": "23330",
        "name": "Salehard",
        "country": "RU",
        "region": "YAN",
        "latitude": 66.5333,
        "longitude": 66.6667,
        "elevation": 16.0,
        "climate_zone_id": 4,
        "is_active": True,
    },
]


PARAMETERS = [
    {"id": 1, "code": "temperature", "name": "Средняя температура", "unit": "°C", "category": "temperature"},
    {"id": 2, "code": "precipitation", "name": "Осадки", "unit": "мм", "category": "precipitation"},
    {"id": 3, "code": "humidity", "name": "Относительная влажность", "unit": "%", "category": "humidity"},
    {"id": 4, "code": "pressure", "name": "Атмосферное давление", "unit": "гПа", "category": "pressure"},
]


SAMPLE_DATA_DIR = Path(__file__).resolve().parent / "data"
ARCTIC_MONTHLY_CSV = SAMPLE_DATA_DIR / "arctic_meteostat_monthly_1995_2024.csv"
TEMPERATURE_PROFILES = {
    1: [-8.2, -6.4, -0.4, 7.4, 14.8, 18.6, 20.5, 18.7, 12.8, 5.9, -0.6, -5.4],
    2: [-2.0, 0.2, 6.8, 13.6, 18.8, 23.6, 26.2, 24.6, 18.4, 10.8, 3.8, -1.1],
    3: [-3.3, 0.8, 7.9, 15.9, 22.0, 26.6, 28.2, 26.9, 21.3, 13.3, 5.1, -1.0],
    4: [5.8, 6.7, 10.0, 15.2, 19.6, 23.0, 26.8, 28.0, 24.2, 18.4, 12.8, 8.0],
}
PRECIPITATION_PROFILES = {
    1: [42.0, 34.0, 39.0, 47.0, 58.0, 73.0, 88.0, 80.0, 62.0, 53.0, 49.0, 45.0],
    2: [32.0, 39.0, 55.0, 78.0, 86.0, 57.0, 34.0, 26.0, 29.0, 46.0, 51.0, 38.0],
    3: [4.0, 6.0, 12.0, 24.0, 38.0, 82.0, 185.0, 166.0, 58.0, 25.0, 10.0, 5.0],
    4: [52.0, 60.0, 112.0, 126.0, 142.0, 176.0, 154.0, 168.0, 214.0, 188.0, 92.0, 57.0],
}
ARCTIC_TEMPERATURE_BASE = [-27.0, -26.0, -20.0, -12.0, -4.0, 4.0, 9.0, 7.0, 1.0, -8.0, -18.0, -24.0]
ARCTIC_PRECIPITATION_BASE = [22.0, 19.0, 18.0, 20.0, 25.0, 34.0, 47.0, 51.0, 43.0, 35.0, 29.0, 25.0]
REAL_MONTHLY_PARAMETER_COLUMNS = {
    1: ("tavg", "temp"),
    2: ("prcp",),
    4: ("pres",),
}


def _safe_float(value: str | None) -> float | None:
    """Преобразует строковое значение CSV в число.

    Args:
        value: Значение из CSV-файла Meteostat.

    Returns:
        Число с плавающей точкой или None для пустого значения.
    """

    if value is None or value == "":
        return None
    try:
        return float(value)
    except ValueError:
        return None


def _first_float(row: dict[str, str], columns: tuple[str, ...]) -> float | None:
    """Возвращает первое числовое значение из CSV-строки.

    Args:
        row: Строка CSV-файла Meteostat.
        columns: Приоритетные имена колонок.

    Returns:
        Первое найденное число или None.
    """

    for column in columns:
        value = _safe_float(row.get(column))
        if value is not None:
            return value
    return None


def _load_arctic_monthly_rows() -> list[dict[str, str]]:
    """Загружает реальные месячные данные арктических станций из CSV.

    Returns:
        Список строк CSV или пустой список, если файл не найден.
    """

    if not ARCTIC_MONTHLY_CSV.exists():
        return []
    with ARCTIC_MONTHLY_CSV.open(encoding="utf-8-sig", newline="") as file:
        return list(csv.DictReader(file))


ARCTIC_MONTHLY_ROWS = _load_arctic_monthly_rows()
REAL_MONTHLY_STATION_IDS = {int(row["station_id"]) for row in ARCTIC_MONTHLY_ROWS if row.get("station_id")}


def _arctic_temperature_profile(station: dict) -> list[float]:
    """Строит месячный температурный профиль для арктической sample-станции.

    Args:
        station: Запись метеостанции из sample dataset.

    Returns:
        Список из 12 среднемесячных температур.
    """

    latitude = float(station["latitude"])
    longitude = float(station["longitude"])
    elevation = float(station.get("elevation") or 0)
    latitude_shift = (70.0 - latitude) * 1.15
    elevation_shift = -elevation / 260.0
    continentality = math.cos(math.radians(longitude - 90.0)) * 1.4
    return [
        round(value + latitude_shift + elevation_shift + continentality * math.sin((index - 5) / 12 * 2 * math.pi), 2)
        for index, value in enumerate(ARCTIC_TEMPERATURE_BASE)
    ]


def _arctic_precipitation_profile(station: dict) -> list[float]:
    """Строит месячный профиль осадков для арктической sample-станции.

    Args:
        station: Запись метеостанции из sample dataset.

    Returns:
        Список из 12 месячных сумм осадков.
    """

    latitude = float(station["latitude"])
    longitude = float(station["longitude"])
    elevation = float(station.get("elevation") or 0)
    coastal_wetness = 1.0 + max(0.0, latitude - 68.0) * 0.035
    elevation_wetness = 1.0 + min(elevation, 200.0) / 1400.0
    longitude_wave = math.sin(math.radians(longitude)) * 5.0
    return [
        round(max(6.0, value * coastal_wetness * elevation_wetness + longitude_wave * math.cos((index - 7) / 12 * 2 * math.pi)), 2)
        for index, value in enumerate(ARCTIC_PRECIPITATION_BASE)
    ]


def _temperature_profile(station: dict) -> list[float]:
    """Возвращает температурный профиль для sample-станции.

    Args:
        station: Запись метеостанции из sample dataset.

    Returns:
        Список из 12 среднемесячных температур.
    """

    return TEMPERATURE_PROFILES.get(int(station["id"])) or _arctic_temperature_profile(station)


def _precipitation_profile(station: dict) -> list[float]:
    """Возвращает профиль осадков для sample-станции.

    Args:
        station: Запись метеостанции из sample dataset.

    Returns:
        Список из 12 месячных сумм осадков.
    """

    return PRECIPITATION_PROFILES.get(int(station["id"])) or _arctic_precipitation_profile(station)


def _real_monthly_observations(start_id: int = 1) -> list[dict]:
    """Преобразует реальные monthly CSV-строки в sample observations.

    Args:
        start_id: Первый идентификатор создаваемого наблюдения.

    Returns:
        Список observations для параметров, присутствующих в CSV.
    """

    observations: list[dict] = []
    observation_id = start_id
    station_ids = {int(station["id"]) for station in STATIONS}
    for row in ARCTIC_MONTHLY_ROWS:
        station_id = int(row["station_id"])
        if station_id not in station_ids:
            continue
        observed_at = row.get("date")
        if not observed_at:
            continue
        for parameter_id, columns in REAL_MONTHLY_PARAMETER_COLUMNS.items():
            value = _first_float(row, columns)
            if value is None:
                continue
            observations.append(
                {
                    "id": observation_id,
                    "station_id": station_id,
                    "parameter_id": parameter_id,
                    "observed_at": observed_at,
                    "value": round(value, 3),
                    "quality_flag": "real_monthly",
                    "source_name": "meteostat_monthly_1995_2024",
                    "created_at": datetime(2026, 1, 1).isoformat(),
                }
            )
            observation_id += 1
    return observations


def build_observations() -> list[dict]:
    """Генерирует детерминированные sample-наблюдения по ORM-структуре backend.

    Returns:
        Список наблюдений с полями станции, параметра, даты, значения и источника.
    """

    observations = _real_monthly_observations()
    observation_id = len(observations) + 1

    for station in STATIONS:
        if int(station["id"]) in REAL_MONTHLY_STATION_IDS:
            continue
        temperature_profile = _temperature_profile(station)
        precipitation_profile = _precipitation_profile(station)
        for year in range(2020, 2025):
            for month in range(1, 13):
                station_id = station["id"]
                month_index = month - 1
                trend = (year - 2020) * 0.18
                year_wave = math.sin((year - 2019) * 1.7 + month * 0.41)
                precipitation_wave = math.cos((year - 2018) * 1.3 + month * 0.73)
                temperature_value = temperature_profile[month_index] + trend + year_wave * 0.35
                precipitation_value = precipitation_profile[month_index] + precipitation_wave * 4.5
                values = {
                    1: round(temperature_value, 2),
                    2: round(max(0, precipitation_value), 2),
                    3: round(62 + math.cos((month - 1) / 12 * 2 * math.pi) * 14 + len(str(station_id)) * 1.5, 2),
                    4: round(1010 + math.cos(month / 12 * 2 * math.pi) * 8 - len(str(station_id)) * 1.2, 2),
                }
                for parameter_id, value in values.items():
                    observations.append(
                        {
                            "id": observation_id,
                            "station_id": station_id,
                            "parameter_id": parameter_id,
                            "observed_at": date(year, month, 1).isoformat(),
                            "value": value,
                            "quality_flag": "sample",
                            "source_name": "klimatika_sample",
                            "created_at": datetime(2026, 1, 1).isoformat(),
                        }
                    )
                    observation_id += 1
    return observations


OBSERVATIONS = build_observations()
