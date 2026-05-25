"""In-process sample API client that mimics the backend REST contract."""

from __future__ import annotations

from collections import defaultdict
from datetime import date, datetime
import json
import math
import statistics
from typing import Any

from app.api.client import ApiError
from app.sample.data import (
    ARCTIC_MONTHLY_ROWS,
    CLIMATE_ZONES,
    OBSERVATIONS,
    PARAMETERS,
    SAMPLE_USER,
    STATIONS,
    generated_observations_for_station,
)


_ANALYSIS_HISTORY: list[dict] = []
_ANALYSIS_RESULTS: dict[int, dict] = {}
_REPORTS: dict[int, dict] = {}
_SAVED_ANALYSIS_SETS: list[dict] = []


def _parse_date(value: str | date) -> date:
    """Преобразует строку или объект date в дату.

    Args:
        value: ISO-строка даты или готовый объект date.

    Returns:
        Объект date.

    Raises:
        ValueError: Если строка не содержит корректную дату.
    """

    if isinstance(value, date):
        return value
    return date.fromisoformat(str(value)[:10])


def _path(path: str) -> str:
    """Нормализует путь sample endpoint до абсолютного вида.

    Args:
        path: Относительный или абсолютный путь API.

    Returns:
        Путь, начинающийся с `/`.
    """

    return path if path.startswith("/") else f"/{path}"


def _parameter(parameter_id: int | str) -> dict:
    """Возвращает sample-запись климатического параметра.

    Args:
        parameter_id: Идентификатор параметра.

    Returns:
        Словарь параметра из sample dataset.

    Raises:
        ApiError: Если параметр не найден.
    """

    pid = int(parameter_id)
    for parameter in PARAMETERS:
        if parameter["id"] == pid:
            return parameter
    raise ApiError("Параметр не найден в sample dataset.", status_code=404, code="PARAMETER_NOT_FOUND")


def _station(station_id: int | str) -> dict:
    """Возвращает sample-запись метеостанции.

    Args:
        station_id: Идентификатор станции.

    Returns:
        Словарь станции из sample dataset.

    Raises:
        ApiError: Если станция не найдена.
    """

    sid = int(station_id)
    for station in STATIONS:
        if station["id"] == sid:
            return station
    raise ApiError("Станция не найдена в sample dataset.", status_code=404, code="STATION_NOT_FOUND")


def _observations(station_id: int | str, parameter_id: int | str, date_from: str, date_to: str) -> list[dict]:
    """Фильтрует sample-наблюдения по станции, параметру и периоду.

    Args:
        station_id: Идентификатор станции.
        parameter_id: Идентификатор параметра.
        date_from: Начальная дата периода в ISO-формате.
        date_to: Конечная дата периода в ISO-формате.

    Returns:
        Список подходящих наблюдений.

    Raises:
        ApiError: Если наблюдения за период не найдены.
        ValueError: Если даты переданы в некорректном формате.
    """

    sid = int(station_id)
    pid = int(parameter_id)
    start = _parse_date(date_from)
    end = _parse_date(date_to)
    station = _station(station_id)
    rows = [
        row
        for row in OBSERVATIONS
        if row["station_id"] == sid and row["parameter_id"] == pid and start <= _parse_date(row["observed_at"]) <= end
    ]
    if not rows:
        rows = [
            row
            for row in generated_observations_for_station(station, parameter_id=pid, start_id=10_000_000)
            if start <= _parse_date(row["observed_at"]) <= end
        ]
    if not rows:
        raise ApiError(
            "В sample dataset нет наблюдений за выбранный период.",
            status_code=404,
            code="OBSERVATIONS_NOT_FOUND",
            context={"station_id": station_id, "parameter_id": parameter_id},
        )
    return rows


def _aggregate(rows: list[dict], aggregation: str) -> list[dict]:
    """Агрегирует наблюдения sample dataset в точки временного ряда.

    Args:
        rows: Наблюдения backend-совместимого формата.
        aggregation: Код агрегации `raw`, `monthly` или `yearly`.

    Returns:
        Список точек с датой и значением.
    """

    if aggregation == "raw":
        return [{"date": row["observed_at"], "value": row["value"]} for row in rows]

    groups: dict[str, list[float]] = defaultdict(list)
    for row in rows:
        observed = _parse_date(row["observed_at"])
        key = f"{observed.year}-01-01" if aggregation == "yearly" else f"{observed.year}-{observed.month:02d}-01"
        groups[key].append(float(row["value"]))
    return [{"date": key, "value": round(statistics.mean(values), 3)} for key, values in sorted(groups.items())]


def _series(params: dict[str, Any]) -> list[dict]:
    """Строит временной ряд по параметрам запроса observations API.

    Args:
        params: Параметры станции, климатического параметра, периода и агрегации.

    Returns:
        Список точек временного ряда.

    Raises:
        ApiError: Если sample-наблюдения не найдены.
    """

    rows = _observations(params["station_id"], params["parameter_id"], params["date_from"], params["date_to"])
    return _aggregate(rows, params.get("aggregation", "monthly"))


def _basic_statistics(values: list[float]) -> dict:
    """Рассчитывает базовые статистики для sample-режима.

    Args:
        values: Числовые значения временного ряда.

    Returns:
        Словарь с count, mean, min, max, std и sum.
    """

    return {
        "count": len(values),
        "mean": round(statistics.mean(values), 3),
        "min": round(min(values), 3),
        "max": round(max(values), 3),
        "std": round(statistics.pstdev(values), 3) if len(values) > 1 else 0.0,
        "sum": round(sum(values), 3),
    }


def _moving_average(series: list[dict], window: int) -> dict:
    """Рассчитывает скользящее среднее для sample-временного ряда.

    Args:
        series: Точки временного ряда с датой и значением.
        window: Размер окна скользящего среднего.

    Returns:
        Словарь результата метода moving_average.
    """

    values = [float(item["value"]) for item in series]
    output = []
    for index, item in enumerate(series):
        start = max(0, index - window + 1)
        output.append({"date": item["date"], "value": round(statistics.mean(values[start : index + 1]), 3)})
    return {"status": "completed", "window": window, "values": output}


def _linear_trend(series: list[dict]) -> dict:
    """Рассчитывает простую линейную тенденцию для sample-ряда.

    Args:
        series: Точки временного ряда с датой и значением.

    Returns:
        Словарь результата linear_trend или failed-статус при нехватке точек.
    """

    values = [float(item["value"]) for item in series]
    n = len(values)
    if n < 2:
        return {"status": "failed", "message": "Недостаточно точек для тренда."}
    x_mean = (n - 1) / 2
    y_mean = statistics.mean(values)
    denominator = sum((i - x_mean) ** 2 for i in range(n))
    slope = sum((i - x_mean) * (value - y_mean) for i, value in enumerate(values)) / denominator
    intercept = y_mean - slope * x_mean
    trend_line = [{"date": item["date"], "value": round(intercept + slope * index, 3)} for index, item in enumerate(series)]
    return {
        "status": "completed",
        "slope": round(slope, 5),
        "intercept": round(intercept, 3),
        "p_value": 0.041 if abs(slope) > 0.01 else 0.41,
        "significant": abs(slope) > 0.01,
        "direction": "warming" if slope > 0 else "cooling" if slope < 0 else "stable",
        "trend_line": {"values": trend_line},
    }


def _climate_norm(series: list[dict]) -> dict:
    """Рассчитывает среднемесячную климатическую норму sample-ряда.

    Args:
        series: Точки временного ряда с датой и значением.

    Returns:
        Словарь результата climate_norm.
    """

    groups: dict[int, list[float]] = defaultdict(list)
    for item in series:
        groups[_parse_date(item["date"]).month].append(float(item["value"]))
    values = [{"month": month, "value": round(statistics.mean(items), 3)} for month, items in sorted(groups.items())]
    return {"status": "completed", "values": values}


def _anomalies(series: list[dict]) -> dict:
    """Рассчитывает отклонения значений от среднего sample-ряда.

    Args:
        series: Точки временного ряда с датой и значением.

    Returns:
        Словарь результата anomalies.
    """

    mean_value = statistics.mean(float(item["value"]) for item in series)
    values = [{"date": item["date"], "value": round(float(item["value"]) - mean_value, 3)} for item in series]
    return {"status": "completed", "baseline_mean": round(mean_value, 3), "values": values}


def _normal_cdf(value: float) -> float:
    """Рассчитывает функцию распределения стандартной нормали.

    Args:
        value: Значение z-статистики.

    Returns:
        Вероятность `P(Z <= value)`.
    """

    return 0.5 * (1 + math.erf(value / math.sqrt(2)))


def _mann_kendall(series: list[dict]) -> dict:
    """Рассчитывает тест Манна-Кендалла для sample-ряда.

    Args:
        series: Точки временного ряда с датой и значением.

    Returns:
        Словарь результата метода `mann_kendall`.
    """

    values = [float(item["value"]) for item in series]
    n = len(values)
    if n < 3:
        return {"status": "failed", "message": "Недостаточно точек для теста Манна-Кендалла."}

    s_statistic = 0
    for first_index in range(n - 1):
        for second_index in range(first_index + 1, n):
            diff = values[second_index] - values[first_index]
            s_statistic += 1 if diff > 0 else -1 if diff < 0 else 0

    tie_correction = 0
    for tied_count in defaultdict(int, {value: values.count(value) for value in set(values)}).values():
        if tied_count > 1:
            tie_correction += tied_count * (tied_count - 1) * (2 * tied_count + 5)

    variance = (n * (n - 1) * (2 * n + 5) - tie_correction) / 18
    if variance <= 0:
        return {
            "status": "completed",
            "s": s_statistic,
            "tau": 0.0,
            "z_score": 0.0,
            "p_value": 1.0,
            "significant": False,
            "direction": "stable",
        }

    if s_statistic > 0:
        z_score = (s_statistic - 1) / math.sqrt(variance)
    elif s_statistic < 0:
        z_score = (s_statistic + 1) / math.sqrt(variance)
    else:
        z_score = 0.0

    tau = s_statistic / (0.5 * n * (n - 1))
    p_value = 2 * (1 - _normal_cdf(abs(z_score)))
    return {
        "status": "completed",
        "s": s_statistic,
        "tau": round(tau, 4),
        "z_score": round(z_score, 4),
        "p_value": round(p_value, 5),
        "significant": p_value < 0.05,
        "direction": "increasing" if tau > 0 else "decreasing" if tau < 0 else "stable",
    }


def _seasonal_decomposition(series: list[dict], period: int = 12) -> dict:
    """Строит простую аддитивную декомпозицию sample-ряда.

    Args:
        series: Точки временного ряда с датой и значением.
        period: Длина сезонного периода в точках.

    Returns:
        Словарь с компонентами trend, seasonal и residual.
    """

    values = [float(item["value"]) for item in series]
    if len(values) < period * 2:
        return {"status": "failed", "message": "Недостаточно точек для сезонной декомпозиции."}

    half_window = max(1, period // 2)
    trend_values = []
    for index in range(len(values)):
        start = max(0, index - half_window)
        end = min(len(values), index + half_window + 1)
        trend_values.append(statistics.mean(values[start:end]))

    seasonal_groups: dict[int, list[float]] = defaultdict(list)
    for index, item in enumerate(series):
        month = _parse_date(item["date"]).month
        seasonal_groups[month].append(values[index] - trend_values[index])
    seasonal_by_month = {
        month: statistics.mean(items)
        for month, items in seasonal_groups.items()
        if items
    }

    trend = []
    seasonal = []
    residual = []
    for index, item in enumerate(series):
        date_value = item["date"]
        month = _parse_date(date_value).month
        seasonal_value = seasonal_by_month.get(month, 0.0)
        residual_value = values[index] - trend_values[index] - seasonal_value
        trend.append({"date": date_value, "value": round(trend_values[index], 3)})
        seasonal.append({"date": date_value, "value": round(seasonal_value, 3)})
        residual.append({"date": date_value, "value": round(residual_value, 3)})

    return {
        "status": "completed",
        "model": "additive",
        "period": period,
        "components": {
            "trend": {"values": trend},
            "seasonal": {"values": seasonal},
            "residual": {"values": residual},
        },
    }


def _quantile(values: list[float], probability: float) -> float:
    """Рассчитывает линейный квантиль для списка чисел.

    Args:
        values: Числовые значения.
        probability: Вероятность квантиля от 0 до 1.

    Returns:
        Значение квантиля.
    """

    if not values:
        return 0.0
    ordered = sorted(values)
    position = (len(ordered) - 1) * probability
    lower = math.floor(position)
    upper = math.ceil(position)
    if lower == upper:
        return ordered[int(position)]
    weight = position - lower
    return ordered[lower] * (1 - weight) + ordered[upper] * weight


def _extremes(series: list[dict], top_n: int = 5) -> dict:
    """Находит экстремальные значения sample-ряда.

    Args:
        series: Точки временного ряда с датой и значением.
        top_n: Количество минимумов и максимумов в таблицах.

    Returns:
        Словарь с порогами, счётчиками, минимумами и максимумами.
    """

    normalized = [{"date": item["date"], "value": float(item["value"])} for item in series]
    values = [item["value"] for item in normalized]
    p05 = _quantile(values, 0.05)
    p95 = _quantile(values, 0.95)
    minima = sorted(normalized, key=lambda item: item["value"])[:top_n]
    maxima = sorted(normalized, key=lambda item: item["value"], reverse=True)[:top_n]
    marked_values = []
    for item in normalized:
        kind = "low" if item["value"] <= p05 else "high" if item["value"] >= p95 else "normal"
        marked_values.append({"date": item["date"], "value": round(item["value"], 3), "kind": kind})
    return {
        "status": "completed",
        "top_n": top_n,
        "thresholds": {"p05": round(p05, 3), "p95": round(p95, 3)},
        "counts": {
            "low": sum(1 for item in marked_values if item["kind"] == "low"),
            "high": sum(1 for item in marked_values if item["kind"] == "high"),
        },
        "minima": [{"date": item["date"], "value": round(item["value"], 3)} for item in minima],
        "maxima": [{"date": item["date"], "value": round(item["value"], 3)} for item in maxima],
        "values": marked_values,
    }


def _analysis_response(payload: dict) -> dict:
    """Формирует ответ sample endpoint `POST /analysis/run`.

    Args:
        payload: JSON-запрос запуска анализа.

    Returns:
        Backend-совместимый JSON результата анализа.

    Raises:
        ApiError: Если исходный временной ряд не найден.
    """

    series = _series(payload)
    values = [float(item["value"]) for item in series]
    methods = payload.get("methods") or ["basic_statistics"]
    options = payload.get("options") or {}
    results: dict[str, Any] = {}

    if "basic_statistics" in methods:
        results["basic_statistics"] = {"status": "completed", **_basic_statistics(values)}
    if "moving_average" in methods:
        results["moving_average"] = _moving_average(series, int(options.get("moving_average_window") or options.get("window") or 12))
    if "linear_trend" in methods:
        results["linear_trend"] = _linear_trend(series)
    if "climate_norm" in methods:
        results["climate_norm"] = _climate_norm(series)
    if "anomalies" in methods:
        results["anomalies"] = _anomalies(series)
    if "mann_kendall" in methods:
        results["mann_kendall"] = _mann_kendall(series)
    if "seasonal_decomposition" in methods:
        results["seasonal_decomposition"] = _seasonal_decomposition(series, int(options.get("seasonal_period") or 12))
    if "extremes" in methods:
        results["extremes"] = _extremes(series, int(options.get("extremes_count") or options.get("top_n") or 5))

    for method in methods:
        results.setdefault(method, {"status": "failed", "message": "Метод не реализован в sample-режиме."})

    run_id = len(_ANALYSIS_HISTORY) + 1
    run = {
        "id": run_id,
        "analysis_run_id": run_id,
        "user_id": SAMPLE_USER["id"],
        "station_id": payload["station_id"],
        "parameter_id": payload["parameter_id"],
        "analysis_type": "timeseries",
        "period_start": payload["date_from"],
        "period_end": payload["date_to"],
        "aggregation": payload.get("aggregation", "monthly"),
        "status": "completed",
        "request_json": payload,
        "created_at": datetime.now().isoformat(),
        "started_at": datetime.now().isoformat(),
        "finished_at": datetime.now().isoformat(),
        "error_message": None,
    }
    response = {
        "analysis_run_id": run_id,
        "status": "completed",
        "station_id": payload["station_id"],
        "parameter_id": payload["parameter_id"],
        "period": {"start": payload["date_from"], "end": payload["date_to"]},
        "aggregation": payload.get("aggregation", "monthly"),
        "timeseries": {"values": series},
        "results": results,
    }
    _ANALYSIS_HISTORY.insert(0, run)
    _ANALYSIS_RESULTS[run_id] = {**run, "result_json": response, "result": response}
    return response


def _period_stats(payload: dict, period: dict) -> dict:
    """Рассчитывает статистики для одного периода сравнения.

    Args:
        payload: Общий JSON-запрос сравнения периодов.
        period: Описание периода с датами `date_from` и `date_to`.

    Returns:
        Словарь периода со статистиками и точками ряда.

    Raises:
        ApiError: Если наблюдения за период не найдены.
    """

    series = _series(
        {
            "station_id": payload["station_id"],
            "parameter_id": payload["parameter_id"],
            "date_from": period["date_from"],
            "date_to": period["date_to"],
            "aggregation": payload.get("aggregation", "monthly"),
        }
    )
    stats = _basic_statistics([float(item["value"]) for item in series])
    return {**period, **stats, "values": series}


def _compare_periods(payload: dict) -> dict:
    """Формирует ответ sample endpoint `POST /comparisons/periods`.

    Args:
        payload: JSON-запрос сравнения двух периодов.

    Returns:
        Словарь с данными периодов, разницей и данными графика.

    Raises:
        ApiError: Если наблюдения для одного из периодов не найдены.
    """

    first = _period_stats(payload, payload["period_1"])
    second = _period_stats(payload, payload["period_2"])
    difference = {
        "mean_absolute": round(second["mean"] - first["mean"], 3),
        "mean_percent": round(((second["mean"] - first["mean"]) / first["mean"]) * 100, 2) if first["mean"] else None,
    }
    return {
        "periods": [{"period": "Период 1", **first}, {"period": "Период 2", **second}],
        "difference": difference,
        "chart_data": [{"period": "Период 1", "mean": first["mean"]}, {"period": "Период 2", "mean": second["mean"]}],
    }


def _compare_stations(payload: dict) -> dict:
    """Формирует ответ sample endpoint `POST /comparisons/stations`.

    Args:
        payload: JSON-запрос сравнения нескольких станций.

    Returns:
        Словарь с выбранной метрикой и отсортированными станциями.

    Raises:
        ApiError: Если станция или наблюдения не найдены.
    """

    metric = payload.get("metric", "mean")
    results = []
    for station_id in payload["station_ids"]:
        station = _station(station_id)
        series = _series(
            {
                "station_id": station_id,
                "parameter_id": payload["parameter_id"],
                "date_from": payload["date_from"],
                "date_to": payload["date_to"],
                "aggregation": payload.get("aggregation", "monthly"),
            }
        )
        stats = _basic_statistics([float(item["value"]) for item in series])
        results.append(
            {
                "station_id": station_id,
                "name": station["name"],
                "code": station["code"],
                "latitude": station["latitude"],
                "longitude": station["longitude"],
                **stats,
                "value": stats.get(metric),
            }
        )
    return {"metric": metric, "stations": sorted(results, key=lambda item: item.get("value") or 0, reverse=True)}


def _rank(values: list[float]) -> list[float]:
    """Преобразует значения в ранги с усреднением связок.

    Args:
        values: Числовые значения.

    Returns:
        Список рангов в исходном порядке.
    """

    indexed = sorted(enumerate(values), key=lambda item: item[1])
    ranks = [0.0] * len(values)
    cursor = 0
    while cursor < len(indexed):
        end = cursor
        while end + 1 < len(indexed) and indexed[end + 1][1] == indexed[cursor][1]:
            end += 1
        rank = (cursor + end + 2) / 2
        for index in range(cursor, end + 1):
            ranks[indexed[index][0]] = rank
        cursor = end + 1
    return ranks


def _pearson(first: list[float], second: list[float]) -> float:
    """Рассчитывает коэффициент корреляции Пирсона.

    Args:
        first: Первый числовой ряд.
        second: Второй числовой ряд.

    Returns:
        Коэффициент корреляции от -1 до 1.
    """

    if len(first) != len(second) or len(first) < 2:
        return 0.0
    first_mean = statistics.mean(first)
    second_mean = statistics.mean(second)
    numerator = sum((x - first_mean) * (y - second_mean) for x, y in zip(first, second, strict=False))
    first_denominator = sum((x - first_mean) ** 2 for x in first)
    second_denominator = sum((y - second_mean) ** 2 for y in second)
    denominator = math.sqrt(first_denominator * second_denominator)
    return numerator / denominator if denominator else 0.0


def _correlation_p_value(correlation: float, sample_size: int) -> float:
    """Оценивает p-value корреляции через преобразование Фишера.

    Args:
        correlation: Коэффициент корреляции.
        sample_size: Количество парных наблюдений.

    Returns:
        Приближённое p-value.
    """

    if sample_size <= 3 or abs(correlation) >= 1:
        return 0.0 if abs(correlation) >= 1 else 1.0
    clipped = max(min(correlation, 0.999999), -0.999999)
    z_score = 0.5 * math.log((1 + clipped) / (1 - clipped)) * math.sqrt(sample_size - 3)
    return 2 * (1 - _normal_cdf(abs(z_score)))


def _parameter_label(parameter: dict) -> str:
    """Формирует краткую подпись sample-параметра.

    Args:
        parameter: Запись климатического параметра.

    Returns:
        Название параметра с единицей измерения.
    """

    return f"{parameter['name']}, {parameter['unit']}"


def _correlation_response(payload: dict) -> dict:
    """Формирует ответ sample endpoint `POST /analysis/correlation`.

    Args:
        payload: JSON-запрос корреляционного анализа.

    Returns:
        Словарь с матрицей корреляций, парами и точками scatter-графиков.

    Raises:
        ApiError: Если выбрано меньше двух параметров или данных недостаточно.
    """

    parameter_ids = payload.get("parameter_ids") or payload.get("parameters") or []
    if len(parameter_ids) < 2:
        raise ApiError("Для корреляции выберите минимум два параметра.", status_code=400, code="NOT_ENOUGH_DATA")

    method = payload.get("method", "pearson")
    series_by_parameter: dict[int, dict[str, float]] = {}
    parameter_records = []
    for parameter_id in parameter_ids:
        parameter = _parameter(parameter_id)
        parameter_records.append(parameter)
        series = _series(
            {
                "station_id": payload["station_id"],
                "parameter_id": parameter_id,
                "date_from": payload["date_from"],
                "date_to": payload["date_to"],
                "aggregation": payload.get("aggregation", "monthly"),
            }
        )
        series_by_parameter[int(parameter_id)] = {item["date"]: float(item["value"]) for item in series}

    common_dates = sorted(set.intersection(*(set(series.keys()) for series in series_by_parameter.values())))
    if len(common_dates) < 3:
        raise ApiError("Недостаточно общих наблюдений для корреляции.", status_code=400, code="NOT_ENOUGH_DATA")

    labels = [_parameter_label(parameter) for parameter in parameter_records]
    values_by_parameter = {
        int(parameter["id"]): [series_by_parameter[int(parameter["id"])][current_date] for current_date in common_dates]
        for parameter in parameter_records
    }
    correlation_values = {
        parameter_id: _rank(values) if method == "spearman" else values
        for parameter_id, values in values_by_parameter.items()
    }

    matrix: list[list[float]] = []
    pairs: list[dict[str, Any]] = []
    for first_parameter in parameter_records:
        row = []
        first_id = int(first_parameter["id"])
        for second_parameter in parameter_records:
            second_id = int(second_parameter["id"])
            coefficient = _pearson(correlation_values[first_id], correlation_values[second_id])
            row.append(round(coefficient, 4))
        matrix.append(row)

    for first_index, first_parameter in enumerate(parameter_records[:-1]):
        for second_parameter in parameter_records[first_index + 1 :]:
            first_id = int(first_parameter["id"])
            second_id = int(second_parameter["id"])
            coefficient = _pearson(correlation_values[first_id], correlation_values[second_id])
            p_value = _correlation_p_value(coefficient, len(common_dates))
            pairs.append(
                {
                    "x_parameter_id": first_id,
                    "x_parameter_name": _parameter_label(first_parameter),
                    "y_parameter_id": second_id,
                    "y_parameter_name": _parameter_label(second_parameter),
                    "correlation": round(coefficient, 4),
                    "p_value": round(p_value, 5),
                    "significant": p_value < 0.05,
                    "n": len(common_dates),
                    "points": [
                        {
                            "date": current_date,
                            "x": values_by_parameter[first_id][index],
                            "y": values_by_parameter[second_id][index],
                        }
                        for index, current_date in enumerate(common_dates)
                    ],
                }
            )

    return {
        "station_id": payload["station_id"],
        "method": method,
        "date_from": payload["date_from"],
        "date_to": payload["date_to"],
        "aggregation": payload.get("aggregation", "monthly"),
        "labels": labels,
        "parameters": [
            {"parameter_id": parameter["id"], "code": parameter["code"], "name": parameter["name"], "unit": parameter["unit"]}
            for parameter in parameter_records
        ],
        "matrix": matrix,
        "pairs": pairs,
    }


def _monthly_norms(station_id: int | str) -> dict[int, dict[str, float | None]]:
    """Возвращает реальные месячные нормы Meteostat для станции.

    Args:
        station_id: Идентификатор метеостанции.

    Returns:
        Словарь `месяц -> нормы температуры и осадков`.
    """

    norms: dict[int, dict[str, float | None]] = {}
    station_key = str(station_id)
    for row in ARCTIC_MONTHLY_ROWS:
        if row.get("station_id") != station_key:
            continue
        month = int(row["month"])
        if month in norms:
            continue
        tavg_norm = row.get("tavg_norm_1995_2024")
        prcp_norm = row.get("prcp_norm_1995_2024")
        norms[month] = {
            "tavg_norm_1995_2024": round(float(tavg_norm), 3) if tavg_norm else None,
            "prcp_norm_1995_2024": round(float(prcp_norm), 3) if prcp_norm else None,
        }
    return norms


def _climatogram(payload: dict) -> dict:
    """Формирует ответ sample endpoint `POST /analysis/climatogram`.

    Args:
        payload: JSON-запрос климатограммы со станцией и параметрами.

    Returns:
        Словарь с месячными температурой и осадками.

    Raises:
        ApiError: Если наблюдения для климатограммы не найдены.
    """

    station_id = payload["station_id"]
    temp_series = _series(
        {
            "station_id": station_id,
            "parameter_id": payload["temperature_parameter_id"],
            "date_from": payload["date_from"],
            "date_to": payload["date_to"],
            "aggregation": "monthly",
        }
    )
    precip_series = _series(
        {
            "station_id": station_id,
            "parameter_id": payload["precipitation_parameter_id"],
            "date_from": payload["date_from"],
            "date_to": payload["date_to"],
            "aggregation": "monthly",
        }
    )
    temp_by_month: dict[int, list[float]] = defaultdict(list)
    precip_by_month: dict[int, list[float]] = defaultdict(list)
    for item in temp_series:
        temp_by_month[_parse_date(item["date"]).month].append(float(item["value"]))
    for item in precip_series:
        precip_by_month[_parse_date(item["date"]).month].append(float(item["value"]))
    months = []
    norms = _monthly_norms(station_id)
    for month in range(1, 13):
        temperature_values = temp_by_month[month]
        precipitation_values = precip_by_month[month]
        if not temperature_values and not precipitation_values:
            continue
        temperature_mean = round(statistics.mean(temperature_values), 3) if temperature_values else None
        precipitation_sum = round(statistics.mean(precipitation_values), 3) if precipitation_values else None
        month_norms = norms.get(month, {})
        months.append(
            {
                "month": month,
                "temperature_mean": temperature_mean,
                "precipitation_sum": precipitation_sum,
                "tavg_norm_1995_2024": month_norms.get("tavg_norm_1995_2024", temperature_mean),
                "prcp_norm_1995_2024": month_norms.get("prcp_norm_1995_2024", precipitation_sum),
            }
        )
    return {"station_id": station_id, "months": months}


def _forecast(payload: dict) -> dict:
    """Формирует демо-прогноз на основе линейного тренда sample-ряда.

    Args:
        payload: JSON-запрос `POST /forecasts/run`.

    Returns:
        Словарь с forecast values и demo-disclaimer.

    Raises:
        ApiError: Если исходный временной ряд не найден.
    """

    series = _series(payload)
    trend = _linear_trend(series)
    slope = float(trend.get("slope") or 0)
    last_date = _parse_date(series[-1]["date"])
    last_value = float(series[-1]["value"])
    horizon = int(payload.get("horizon") or 12)
    values = []
    for step in range(1, horizon + 1):
        year = last_date.year + ((last_date.month - 1 + step) // 12)
        month = ((last_date.month - 1 + step) % 12) + 1
        values.append({"date": date(year, month, 1).isoformat(), "value": round(last_value + slope * step, 3)})
    return {
        "forecast_id": 1,
        "model": payload.get("model", "linear_trend"),
        "horizon": horizon,
        "horizon_unit": payload.get("horizon_unit", "months"),
        "forecast": {"values": values},
        "disclaimer": "Sample forecast is deterministic demo data.",
    }


class SampleApiClient:
    """Эмулирует backend REST API в памяти для локального sample-режима.

    Attributes:
        token: JWT-совместимое значение токена, сохранённое для совместимости с ApiClient.
    """

    def __init__(self, token: str | None = None) -> None:
        """Инициализирует sample API-клиент.

        Args:
            token: JWT-токен пользователя или None.

        Returns:
            None.
        """

        self.token = token

    def get(self, path: str, params: dict[str, Any] | None = None) -> Any:
        """Обрабатывает sample GET-запрос к in-process API.

        Args:
            path: Путь backend endpoint без базового URL.
            params: Query-параметры запроса.

        Returns:
            JSON-совместимый ответ sample API.

        Raises:
            ApiError: Если endpoint или ресурс не найден.
        """

        params = params or {}
        path = _path(path)
        if path == "/health":
            return {"status": "ok", "service": "КлиматикА sample backend", "mode": "sample"}
        if path == "/users/me":
            return SAMPLE_USER
        if path == "/climate-zones":
            return {"items": CLIMATE_ZONES}
        if path.startswith("/climate-zones/"):
            zone_id = int(path.rsplit("/", 1)[1])
            return next(zone for zone in CLIMATE_ZONES if zone["id"] == zone_id)
        if path == "/stations":
            return {"items": STATIONS}
        if path.startswith("/stations/"):
            return _station(path.rsplit("/", 1)[1])
        if path == "/parameters":
            return {"items": PARAMETERS}
        if path.startswith("/parameters/"):
            return _parameter(path.rsplit("/", 1)[1])
        if path == "/observations/availability":
            rows = _observations(params["station_id"], params["parameter_id"], "1900-01-01", "2100-01-01")
            return {"date_min": rows[0]["observed_at"], "date_max": rows[-1]["observed_at"], "count": len(rows), "missing_estimate": 0}
        if path == "/observations/timeseries":
            return {"values": _series(params)}
        if path == "/analysis/history":
            return {"items": _ANALYSIS_HISTORY}
        if path == "/saved-analysis-sets":
            return {"items": _SAVED_ANALYSIS_SETS}
        if path.startswith("/analysis/"):
            run_id = int(path.rsplit("/", 1)[1])
            if run_id not in _ANALYSIS_RESULTS:
                raise ApiError("Analysis run не найден в sample dataset.", status_code=404, code="ANALYSIS_NOT_FOUND")
            return _ANALYSIS_RESULTS[run_id]
        raise ApiError(f"Sample endpoint не реализован: GET {path}", status_code=404, code="SAMPLE_ENDPOINT_NOT_FOUND")

    def post(self, path: str, json: dict[str, Any] | None = None) -> Any:
        """Обрабатывает sample POST-запрос к in-process API.

        Args:
            path: Путь backend endpoint без базового URL.
            json: JSON-тело запроса.

        Returns:
            JSON-совместимый ответ sample API.

        Raises:
            ApiError: Если endpoint или связанные данные не найдены.
        """

        payload = json or {}
        path = _path(path)
        if path == "/auth/register":
            return {**SAMPLE_USER, "email": payload.get("email", SAMPLE_USER["email"]), "full_name": payload.get("full_name")}
        if path == "/auth/login":
            return {"access_token": "sample-jwt-token", "token_type": "bearer"}
        if path == "/analysis/run":
            return _analysis_response(payload)
        if path == "/analysis/climatogram":
            return _climatogram(payload)
        if path == "/analysis/correlation":
            return _correlation_response(payload)
        if path == "/comparisons/periods":
            return _compare_periods(payload)
        if path == "/comparisons/stations":
            return _compare_stations(payload)
        if path == "/forecasts/run":
            return _forecast(payload)
        if path == "/saved-analysis-sets":
            saved_set_id = len(_SAVED_ANALYSIS_SETS) + 1
            record = {
                "id": saved_set_id,
                "user_id": SAMPLE_USER["id"],
                "station_id": payload.get("station_id"),
                "parameter_id": payload.get("parameter_id"),
                "selected_parameters": payload.get("selected_parameters") or [],
                "period_start": payload.get("period_start"),
                "period_end": payload.get("period_end"),
                "mode": payload.get("mode", "dashboard"),
                "created_at": datetime.now().isoformat(),
            }
            _SAVED_ANALYSIS_SETS.insert(0, record)
            return record
        if path == "/reports":
            report_id = len(_REPORTS) + 1
            analysis_run_id = int(payload["analysis_run_id"])
            report = {
                "id": report_id,
                "report_id": report_id,
                "analysis_run_id": analysis_run_id,
                "status": "completed",
                "download_url": f"/api/v1/reports/{report_id}/download",
                "content_json": _ANALYSIS_RESULTS.get(analysis_run_id, {}),
                "created_at": datetime.now().isoformat(),
            }
            _REPORTS[report_id] = report
            return report
        raise ApiError(f"Sample endpoint не реализован: POST {path}", status_code=404, code="SAMPLE_ENDPOINT_NOT_FOUND")

    def download(self, path: str, params: dict[str, Any] | None = None) -> bytes:
        """Обрабатывает sample скачивание отчёта.

        Args:
            path: Путь endpoint скачивания отчёта.
            params: Query-параметры запроса, сохранены для совместимости.

        Returns:
            Байты JSON-отчёта.

        Raises:
            ApiError: Если endpoint или отчёт не найден.
        """

        path = _path(path)
        if path.startswith("/reports/") and path.endswith("/download"):
            report_id = int(path.split("/")[2])
            if report_id not in _REPORTS:
                raise ApiError("Отчёт не найден в sample dataset.", status_code=404, code="REPORT_NOT_FOUND")
            return json.dumps(_REPORTS[report_id], ensure_ascii=False, indent=2).encode("utf-8")
        raise ApiError(f"Sample endpoint не реализован: DOWNLOAD {path}", status_code=404, code="SAMPLE_ENDPOINT_NOT_FOUND")
