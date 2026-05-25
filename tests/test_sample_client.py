from __future__ import annotations

import json

from app.sample.client import SampleApiClient


def _polygon_area(points: list[tuple[float, float]]) -> float:
    """Рассчитывает площадь многоугольника по формуле Гаусса.

    Args:
        points: Точки контура в порядке обхода.

    Returns:
        Абсолютная площадь многоугольника.
    """

    if len(points) < 3:
        return 0.0
    pairs = zip(points, [*points[1:], points[0]])
    return abs(sum(x1 * y2 - x2 * y1 for (x1, y1), (x2, y2) in pairs)) / 2


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
        "methods": [
            "basic_statistics",
            "moving_average",
            "linear_trend",
            "climate_norm",
            "anomalies",
            "mann_kendall",
            "seasonal_decomposition",
            "extremes",
        ],
        "options": {"moving_average_window": 12, "extremes_count": 5},
    }
    result = client.post("/analysis/run", json=payload)
    assert result["status"] == "completed"
    assert "basic_statistics" in result["results"]
    assert result["results"]["mann_kendall"]["status"] == "completed"
    assert result["results"]["seasonal_decomposition"]["status"] == "completed"
    assert result["results"]["extremes"]["status"] == "completed"
    assert result["results"]["extremes"]["minima"]
    assert result["results"]["extremes"]["maxima"]
    assert "p05" in result["results"]["extremes"]["thresholds"]

    history = client.get("/analysis/history")["items"]
    assert history[0]["analysis_run_id"] == result["analysis_run_id"]

    report = client.post("/reports", json={"analysis_run_id": result["analysis_run_id"]})
    content = json.loads(client.download(f"/reports/{report['report_id']}/download").decode("utf-8"))
    assert content["analysis_run_id"] == result["analysis_run_id"]


def test_sample_client_contains_arctic_stations() -> None:
    """Проверяет наличие добавленных арктических станций и наблюдений.

    Returns:
        None.
    """

    client = SampleApiClient(token="sample")
    stations = client.get("/stations")["items"]
    arctic_station = next(station for station in stations if station["code"] == "20674")
    availability = client.get(
        "/observations/availability",
        params={"station_id": arctic_station["id"], "parameter_id": 1},
    )

    assert len(stations) >= 7530
    assert arctic_station["name"] == "Ostrov Dikson"
    assert availability["date_min"] == "1995-01-01"
    assert availability["date_max"] == "2024-12-01"
    assert availability["count"] == 360


def test_sample_client_loads_eurasia_stations_from_sqlite() -> None:
    """Проверяет загрузку большого справочника станций из SQLite.

    Returns:
        None.
    """

    client = SampleApiClient(token="sample")
    stations = client.get("/stations")["items"]
    imported_station = next(station for station in stations if station.get("source_id") == "OMAM0")
    availability = client.get(
        "/observations/availability",
        params={"station_id": imported_station["id"], "parameter_id": 1},
    )

    assert imported_station["code"] == "OMAM0"
    assert imported_station["country"] == "AE"
    assert availability["count"] == 60


def test_sample_client_saves_analysis_set_per_station() -> None:
    """Проверяет sample-сохранение пользовательского набора анализа.

    Returns:
        None.
    """

    client = SampleApiClient(token="sample")
    record = client.post(
        "/saved-analysis-sets",
        json={
            "station_id": 20674,
            "parameter_id": 1,
            "selected_parameters": [1, 2],
            "period_start": "1995-01-01",
            "period_end": "2024-12-01",
            "mode": "dashboard",
        },
    )
    saved_sets = client.get("/saved-analysis-sets")["items"]

    assert record["id"]
    assert record["station_id"] == 20674
    assert record["parameter_id"] == 1
    assert record["selected_parameters"] == [1, 2]
    assert saved_sets[0]["id"] == record["id"]


def test_sample_client_returns_correlation_matrix_and_pairs() -> None:
    """Проверяет sample-ответ корреляционного анализа.

    Returns:
        None.
    """

    client = SampleApiClient(token="sample")
    station = client.get("/stations")["items"][0]
    parameters = client.get("/parameters")["items"][:3]
    result = client.post(
        "/analysis/correlation",
        json={
            "station_id": station["id"],
            "parameter_ids": [parameter["id"] for parameter in parameters],
            "date_from": "2020-01-01",
            "date_to": "2024-12-01",
            "aggregation": "monthly",
            "method": "pearson",
        },
    )

    assert len(result["labels"]) == 3
    assert len(result["matrix"]) == 3
    assert len(result["pairs"]) == 3
    assert result["pairs"][0]["points"]


def test_sample_client_climatogram_returns_norm_fields() -> None:
    """Проверяет поля норм в sample-ответе климатограммы.

    Returns:
        None.
    """

    client = SampleApiClient(token="sample")
    station = client.get("/stations")["items"][0]
    result = client.post(
        "/analysis/climatogram",
        json={
            "station_id": station["id"],
            "temperature_parameter_id": 1,
            "precipitation_parameter_id": 2,
            "date_from": "2020-01-01",
            "date_to": "2024-12-01",
        },
    )

    assert len(result["months"]) == 12
    assert "tavg_norm_1995_2024" in result["months"][0]
    assert "prcp_norm_1995_2024" in result["months"][0]


def test_sample_client_uses_real_arctic_monthly_data() -> None:
    """Проверяет использование реальных monthly-данных для арктической станции.

    Returns:
        None.
    """

    client = SampleApiClient(token="sample")
    result = client.post(
        "/analysis/climatogram",
        json={
            "station_id": 20674,
            "temperature_parameter_id": 1,
            "precipitation_parameter_id": 2,
            "date_from": "1995-01-01",
            "date_to": "2024-12-01",
        },
    )
    january = result["months"][0]

    assert january["temperature_mean"] == -23.753
    assert january["precipitation_sum"] == 35.7
    assert january["tavg_norm_1995_2024"] == -23.753
    assert january["prcp_norm_1995_2024"] == 35.7


def test_sample_client_climatogram_has_non_linear_polygon() -> None:
    """Проверяет, что sample-климатограмма образует заметный многоугольник.

    Returns:
        None.
    """

    client = SampleApiClient(token="sample")
    station = client.get("/stations")["items"][0]
    result = client.post(
        "/analysis/climatogram",
        json={
            "station_id": station["id"],
            "temperature_parameter_id": 1,
            "precipitation_parameter_id": 2,
            "date_from": "2020-01-01",
            "date_to": "2024-12-01",
        },
    )
    points = [
        (month["tavg_norm_1995_2024"], month["prcp_norm_1995_2024"])
        for month in result["months"]
    ]

    assert _polygon_area(points) > 100
