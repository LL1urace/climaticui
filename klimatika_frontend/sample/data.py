"""Deterministic sample data shaped after the backend ORM models."""

from __future__ import annotations

from datetime import date, datetime
import math


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
]


PARAMETERS = [
    {"id": 1, "code": "temperature", "name": "Средняя температура", "unit": "°C", "category": "temperature"},
    {"id": 2, "code": "precipitation", "name": "Осадки", "unit": "мм", "category": "precipitation"},
    {"id": 3, "code": "humidity", "name": "Относительная влажность", "unit": "%", "category": "humidity"},
    {"id": 4, "code": "pressure", "name": "Атмосферное давление", "unit": "гПа", "category": "pressure"},
]


def build_observations() -> list[dict]:
    """Генерирует детерминированные sample-наблюдения по ORM-структуре backend.

    Returns:
        Список наблюдений с полями станции, параметра, даты, значения и источника.
    """

    observations: list[dict] = []
    observation_id = 1
    station_bias = {1: -2.0, 2: 2.5, 3: 5.0, 4: 9.0}
    precipitation_bias = {1: 46.0, 2: 34.0, 3: 42.0, 4: 72.0}

    for station in STATIONS:
        for year in range(2020, 2025):
            for month in range(1, 13):
                seasonal = math.sin((month - 3) / 12 * 2 * math.pi)
                trend = (year - 2020) * 0.18
                station_id = station["id"]
                values = {
                    1: round(7 + station_bias[station_id] + seasonal * 14 + trend, 2),
                    2: round(max(0, precipitation_bias[station_id] + math.cos(month / 12 * 2 * math.pi) * 22 + (month % 3) * 4), 2),
                    3: round(62 + math.cos((month - 1) / 12 * 2 * math.pi) * 14 + station_id * 1.5, 2),
                    4: round(1010 + math.cos(month / 12 * 2 * math.pi) * 8 - station_id * 1.2, 2),
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
