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
    real_station_codes = {
        "20674",
        "20744",
        "20891",
        "20967",
        "21432",
        "21504",
        "21647",
        "21802",
        "21824",
        "21921",
        "21931",
        "21946",
        "22113",
        "22217",
        "23022",
        "23205",
        "23330",
        "25042",
        "25062",
        "25123",
    }
    station_codes = {str(station["code"]) for station in stations}
    real_flagged_codes = {
        str(station["code"])
        for station in stations
        if station.get("has_real_monthly_data") and station.get("data_quality") == "real_monthly"
    }
    arctic_station = next(station for station in stations if station["code"] == "20674")
    availability = client.get(
        "/observations/availability",
        params={"station_id": arctic_station["id"], "parameter_id": 1},
    )

    assert len(stations) >= 7530
    assert real_station_codes <= station_codes
    assert real_station_codes <= real_flagged_codes
    assert arctic_station["name"] == "Ostrov Dikson"
    assert availability["date_min"] == "1936-01-01"
    assert availability["date_max"] == "2026-05-01"
    assert availability["count"] == 1085


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
            "aggregation": "yearly",
            "mode": "dashboard",
            "modes": ["dashboard", "forecast", "correlation"],
            "session_snapshot": {
                "forecast_model": "neural_mlp",
                "correlation_method": "spearman",
            },
        },
    )
    saved_sets = client.get("/saved-analysis-sets")["items"]

    assert record["id"]
    assert record["station_id"] == 20674
    assert record["parameter_id"] == 1
    assert record["selected_parameters"] == [1, 2]
    assert record["aggregation"] == "yearly"
    assert record["modes"] == ["dashboard", "forecast", "correlation"]
    assert record["session_snapshot"]["forecast_model"] == "neural_mlp"
    assert saved_sets[0]["id"] == record["id"]


def test_sample_client_returns_raw_observation_slice() -> None:
    """Проверяет выгрузку полного сырого среза наблюдений без агрегации."""

    client = SampleApiClient(token="sample")
    result = client.get(
        "/observations",
        params={
            "station_id": 20674,
            "parameter_id": 1,
            "date_from": "2020-01-01",
            "date_to": "2020-12-31",
        },
    )

    rows = result["items"]
    assert len(rows) == 366
    assert rows[0]["observed_at"] == "2020-01-01"
    assert rows[-1]["observed_at"] == "2020-12-31"
    assert rows[0]["source_name"] == "local_meteostat_daily_csv_gz"
    assert all(str(row["station_id"]) == "20674" for row in rows)


def test_sample_station_comparison_can_skip_missing_series() -> None:
    """Проверяет пропуск станций без данных в режиме тематической карты."""

    client = SampleApiClient(token="sample")
    imported_station = next(station for station in client.get("/stations")["items"] if station.get("source_id") == "OMAM0")
    result = client.post(
        "/comparisons/stations",
        json={
            "station_ids": [imported_station["id"]],
            "parameter_id": 1,
            "date_from": "1990-01-01",
            "date_to": "1991-01-01",
            "aggregation": "monthly",
            "metric": "mean",
            "skip_missing": True,
        },
    )

    assert result["stations"] == []
    assert result["skipped_stations"] == 1


def test_sample_client_runs_forecast_models() -> None:
    """Проверяет базовые клиентские модели прогнозирования."""

    client = SampleApiClient(token="sample")
    models = [
        "linear_trend",
        "moving_average",
        "seasonal_naive",
        "exponential_smoothing",
        "trend_seasonal",
        "neural_mlp",
        "neural_seasonal_mlp",
    ]

    for model in models:
        result = client.post(
            "/forecasts/run",
            json={
                "station_id": 20674,
                "parameter_id": 1,
                "date_from": "2020-01-01",
                "date_to": "2024-12-01",
                "aggregation": "monthly",
                "model": model,
                "training_mode": "fit_selected_period",
                "horizon": 6,
                "horizon_unit": "months",
                "options": {"window": 6, "seasonal_period": 12, "alpha": 0.35, "hidden_units": 12},
            },
        )
        values = result["forecast"]["values"]

        assert result["status"] == "completed"
        assert result["model"] == model
        assert result["training"]["mode"] == "fit_selected_period"
        assert result["metrics"]["status"] == "completed"
        assert len(values) == 6
        assert values[0]["date"] == "2025-01-01"
        assert all(isinstance(item["value"], float) for item in values)


def test_sample_client_forecast_pretraining_uses_extended_history() -> None:
    """Проверяет режим предобучения на расширенной истории станции."""

    client = SampleApiClient(token="sample")
    result = client.post(
        "/forecasts/run",
        json={
            "station_id": 20674,
            "parameter_id": 1,
            "date_from": "2024-01-01",
            "date_to": "2024-12-01",
            "aggregation": "monthly",
            "model": "trend_seasonal",
            "training_mode": "pretrained_station",
            "horizon": 3,
            "horizon_unit": "months",
            "options": {"seasonal_period": 12},
        },
    )

    assert result["training"]["mode"] == "pretrained_station"
    assert result["training"]["selected_period_observations"] == 12
    assert result["training"]["observations"] > result["training"]["selected_period_observations"]
    assert result["model_params"]["seasonal_months"] == 12
    assert len(result["forecast"]["values"]) == 3


def test_sample_client_neural_forecast_returns_model_params() -> None:
    """Проверяет нейросетевой прогноз с сезонными признаками."""

    client = SampleApiClient(token="sample")
    result = client.post(
        "/forecasts/run",
        json={
            "station_id": 20674,
            "parameter_id": 1,
            "date_from": "2020-01-01",
            "date_to": "2024-12-01",
            "aggregation": "monthly",
            "model": "neural_seasonal_mlp",
            "training_mode": "pretrained_station",
            "horizon": 4,
            "horizon_unit": "months",
            "options": {"window": 12, "hidden_units": 16, "ridge": 0.001},
        },
    )

    assert result["model"] == "neural_seasonal_mlp"
    assert result["station"]["station_id"] == 20674
    assert result["model_params"]["network_type"] == "single_hidden_layer_mlp"
    assert result["model_params"]["features"] == "lags_calendar_station"
    assert result["model_params"]["station_features_used"] is True
    assert result["model_params"]["station_feature_names"] == ["latitude", "longitude", "elevation"]
    assert result["model_params"]["training_samples"] > 0
    assert len(result["forecast"]["values"]) == 4
    assert all(isinstance(item["value"], float) for item in result["forecast"]["values"])


def test_sample_client_neural_forecast_changes_between_stations() -> None:
    """Проверяет, что MLP-прогноз учитывает выбранную станцию."""

    client = SampleApiClient(token="sample")
    base_payload = {
        "parameter_id": 1,
        "date_from": "2020-01-01",
        "date_to": "2024-12-01",
        "aggregation": "monthly",
        "model": "neural_seasonal_mlp",
        "training_mode": "pretrained_station",
        "horizon": 4,
        "horizon_unit": "months",
        "options": {"window": 12, "hidden_units": 16, "ridge": 0.001},
    }

    first = client.post("/forecasts/run", json={**base_payload, "station_id": 20674})
    second = client.post("/forecasts/run", json={**base_payload, "station_id": 21824})
    first_values = [item["value"] for item in first["forecast"]["values"]]
    second_values = [item["value"] for item in second["forecast"]["values"]]

    assert first["station"]["station_id"] == 20674
    assert second["station"]["station_id"] == 21824
    assert first_values != second_values


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
