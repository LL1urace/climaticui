"""Report section discovery and content assembly."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Mapping

import pandas as pd
import plotly.graph_objects as go

from app.reports.figures import (
    build_anomaly_figure,
    build_bar_chart_figure,
    build_climatogram_report_figures,
    build_correlation_heatmap_figure,
    build_correlation_scatter_figures,
    build_decomposition_figure,
    build_extremes_figure,
    build_forecast_figure,
    build_grouped_bar_chart_figure,
    build_multi_timeseries_figure,
    build_overlay_figure,
    build_station_map_figure,
    build_timeseries_figure,
)
from app.utils.formatters import format_metric_label, result_payload, station_id, station_label, unwrap_records


@dataclass(frozen=True)
class ReportSection:
    """Описывает раздел отчёта, доступный пользователю.

    Attributes:
        id: Стабильный идентификатор раздела.
        title: Название раздела для UI и PDF.
        description: Краткое описание содержимого.
        page_hint: Подсказка, где сначала построить результат.
        available: Доступен ли раздел для включения в PDF.
        reason: Причина недоступности раздела.
    """

    id: str
    title: str
    description: str
    page_hint: str
    available: bool
    reason: str = ""


@dataclass(frozen=True)
class ReportTable:
    """Описывает табличный блок PDF-отчёта.

    Attributes:
        title: Заголовок таблицы.
        rows: Строки таблицы в виде словарей.
    """

    title: str
    rows: list[dict[str, Any]]


@dataclass(frozen=True)
class ReportBlock:
    """Описывает готовый блок PDF-отчёта.

    Attributes:
        id: Идентификатор исходного раздела.
        title: Заголовок блока.
        description: Краткое пояснение блока.
        notes: Текстовые примечания.
        tables: Таблицы для вставки в PDF.
        figures: Plotly-графики для экспорта в PNG.
    """

    id: str
    title: str
    description: str = ""
    notes: list[str] = field(default_factory=list)
    tables: list[ReportTable] = field(default_factory=list)
    figures: list[go.Figure] = field(default_factory=list)


SECTION_DEFINITIONS = {
    "dashboard": {
        "title": "Сводка исследовательской панели",
        "description": "Выбранные станции, период, агрегация и географический срез.",
        "page_hint": "Откройте «Исследовательскую панель» и выберите станции или период.",
    },
    "analysis": {
        "title": "Анализ временного ряда",
        "description": "Базовая статистика, нормы, аномалии, тренды, сглаживание и экстремумы.",
        "page_hint": "Сначала запустите страницу «Анализ».",
    },
    "period_comparison": {
        "title": "Сравнение периодов",
        "description": "Сравнение статистик между несколькими временными интервалами.",
        "page_hint": "Сначала запустите страницу «Сравнение периодов».",
    },
    "station_comparison": {
        "title": "Сравнение станций",
        "description": "Сопоставление выбранных метеостанций по одному показателю.",
        "page_hint": "Сначала запустите страницу «Сравнение станций».",
    },
    "climatogram": {
        "title": "Климатограммы",
        "description": "Месячные профили температуры и осадков, включая точечную климатограмму.",
        "page_hint": "Сначала постройте климатограмму.",
    },
    "forecast": {
        "title": "Прогнозирование",
        "description": "Исследовательский прогноз по выбранному временному ряду.",
        "page_hint": "Сначала запустите страницу «Прогнозирование».",
    },
    "correlation": {
        "title": "Корреляционный анализ",
        "description": "Матрица и диаграммы связи между климатическими параметрами.",
        "page_hint": "Сначала рассчитайте корреляции.",
    },
}


def _has_value(state: Mapping[str, Any], key: str) -> bool:
    """Проверяет наличие непустого значения в состоянии.

    Args:
        state: Mapping session state.
        key: Ключ состояния.

    Returns:
        True, если значение существует и не пустое.
    """

    value = state.get(key)
    return value not in (None, "", [], {})


def _definition(section_id: str) -> dict[str, str]:
    """Возвращает описание раздела по идентификатору.

    Args:
        section_id: Идентификатор раздела.

    Returns:
        Словарь с названием, описанием и подсказкой.
    """

    return SECTION_DEFINITIONS[section_id]


def collect_report_sections(state: Mapping[str, Any]) -> list[ReportSection]:
    """Собирает список доступных и недоступных разделов отчёта.

    Args:
        state: Streamlit session state или совместимый mapping.

    Returns:
        Список разделов с флагом доступности.
    """

    availability = {
        "dashboard": _has_value(state, "dashboard_station_ids") or _has_value(state, "dashboard_date_from"),
        "analysis": _has_value(state, "last_analysis_result"),
        "period_comparison": _has_value(state, "last_period_comparison"),
        "station_comparison": _has_value(state, "last_station_comparison"),
        "climatogram": _has_value(state, "last_climatogram_items"),
        "forecast": _has_value(state, "last_forecast"),
        "correlation": _has_value(state, "last_correlation_result"),
    }
    sections = []
    for section_id in SECTION_DEFINITIONS:
        definition = _definition(section_id)
        available = bool(availability[section_id])
        sections.append(
            ReportSection(
                id=section_id,
                title=definition["title"],
                description=definition["description"],
                page_hint=definition["page_hint"],
                available=available,
                reason="" if available else definition["page_hint"],
            )
        )
    return sections


def available_section_ids(state: Mapping[str, Any]) -> list[str]:
    """Возвращает идентификаторы доступных разделов.

    Args:
        state: Streamlit session state или совместимый mapping.

    Returns:
        Список ID разделов, которые можно включить в PDF.
    """

    return [section.id for section in collect_report_sections(state) if section.available]


def _method_payload(results: dict[str, Any], name: str) -> dict[str, Any]:
    """Возвращает payload конкретного метода анализа.

    Args:
        results: Словарь результатов анализа.
        name: Код метода анализа.

    Returns:
        Словарь результата метода или пустой словарь.
    """

    payload = results.get(name)
    if isinstance(payload, dict) and isinstance(payload.get("result"), dict):
        return payload["result"]
    return payload if isinstance(payload, dict) else {}


def _scalar_rows(payload: dict[str, Any]) -> list[dict[str, Any]]:
    """Преобразует скалярные значения словаря в строки таблицы.

    Args:
        payload: JSON результата метода или метрик.

    Returns:
        Строки вида `Показатель` и `Значение`.
    """

    rows = []
    for key, value in payload.items():
        if key == "status" or isinstance(value, (dict, list)):
            continue
        rows.append({"Показатель": format_metric_label(str(key)), "Значение": value})
    return rows


def _table_rows(payload: Any, preferred_keys: tuple[str, ...] = ("values", "series", "data", "items", "records")) -> list[dict[str, Any]]:
    """Нормализует произвольный JSON в строки таблицы.

    Args:
        payload: JSON-ответ, список или словарь.
        preferred_keys: Ключи, где ожидается коллекция строк.

    Returns:
        Список строк для PDF-таблицы.
    """

    records = unwrap_records(payload, preferred_keys)
    if records:
        return records
    if isinstance(payload, dict):
        if isinstance(payload.get("metrics"), dict):
            return _scalar_rows(payload["metrics"])
        return _scalar_rows(payload)
    return []


def _selected_station_records(state: Mapping[str, Any], station_ids: list[Any] | None = None) -> list[dict[str, Any]]:
    """Возвращает записи выбранных станций из кэша справочника.

    Args:
        state: Streamlit session state или совместимый mapping.
        station_ids: Идентификаторы выбранных станций.

    Returns:
        Список записей станций.
    """

    stations = state.get("cached_stations") or []
    selected_ids = station_ids if station_ids is not None else state.get("dashboard_station_ids") or []
    selected_keys = {str(item) for item in selected_ids}
    if not selected_keys:
        return []
    return [station for station in stations if str(station_id(station)) in selected_keys]


def _safe_float(value: Any) -> float | None:
    """Преобразует значение в float.

    Args:
        value: Исходное значение.

    Returns:
        Число или None, если преобразование невозможно.
    """

    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _dashboard_tables(state: Mapping[str, Any]) -> list[ReportTable]:
    """Готовит таблицы сводки исследовательской панели.

    Args:
        state: Streamlit session state или совместимый mapping.

    Returns:
        Таблицы для dashboard-раздела PDF.
    """

    stations = _selected_station_records(state)
    date_from = state.get("dashboard_date_from")
    date_to = state.get("dashboard_date_to")
    latitudes = [_safe_float(station.get("latitude")) for station in stations]
    longitudes = [_safe_float(station.get("longitude")) for station in stations]
    elevations = [_safe_float(station.get("elevation")) for station in stations]
    latitudes = [value for value in latitudes if value is not None]
    longitudes = [value for value in longitudes if value is not None]
    elevations = [value for value in elevations if value is not None]
    period_days = (date_to - date_from).days + 1 if date_from and date_to else None
    summary = [
        {"Показатель": "Выбрано станций", "Значение": len(stations)},
        {"Показатель": "Период", "Значение": f"{date_from} - {date_to}" if date_from and date_to else "не выбран"},
        {"Показатель": "Агрегация", "Значение": state.get("dashboard_aggregation") or "не выбрана"},
        {"Показатель": "Длительность периода", "Значение": f"{period_days} дней" if period_days else "не выбрана"},
        {
            "Показатель": "Широтный охват",
            "Значение": f"{max(latitudes) - min(latitudes):.2f}°" if len(latitudes) > 1 else "0.00°" if latitudes else "n/a",
        },
        {
            "Показатель": "Долготный охват",
            "Значение": f"{max(longitudes) - min(longitudes):.2f}°" if len(longitudes) > 1 else "0.00°" if longitudes else "n/a",
        },
        {
            "Показатель": "Средняя высота",
            "Значение": f"{sum(elevations) / len(elevations):.0f} м" if elevations else "n/a",
        },
    ]
    station_rows = [
        {
            "Станция": station_label(station),
            "Код": station.get("code"),
            "Страна": station.get("country"),
            "Регион": station.get("region"),
            "Широта": station.get("latitude"),
            "Долгота": station.get("longitude"),
            "Высота, м": station.get("elevation"),
        }
        for station in stations
    ]
    tables = [ReportTable("Сводка выбранного среза", summary)]
    if station_rows:
        tables.append(ReportTable("Выбранные метеостанции", station_rows))
    return tables


def _analysis_tables(results: dict[str, Any]) -> list[ReportTable]:
    """Готовит таблицы раздела анализа.

    Args:
        results: Нормализованный JSON результата анализа.

    Returns:
        Таблицы для PDF.
    """

    tables: list[ReportTable] = []
    basic_statistics = _method_payload(results, "basic_statistics")
    climate_norm = _method_payload(results, "climate_norm")
    mann_kendall = _method_payload(results, "mann_kendall")
    extremes = _method_payload(results, "extremes")
    for title, payload in (
        ("Базовая статистика", basic_statistics.get("metrics") if isinstance(basic_statistics.get("metrics"), dict) else basic_statistics),
        ("Климатические нормы", climate_norm),
        ("Тест Манна-Кендалла", mann_kendall),
    ):
        rows = _table_rows(payload)
        if rows:
            tables.append(ReportTable(title, rows))
    if isinstance(extremes, dict):
        metrics = {}
        if isinstance(extremes.get("thresholds"), dict):
            metrics.update(extremes["thresholds"])
        if isinstance(extremes.get("counts"), dict):
            metrics.update(extremes["counts"])
        if extremes.get("top_n") is not None:
            metrics["top_n"] = extremes["top_n"]
        metric_rows = _table_rows(metrics)
        if metric_rows:
            tables.append(ReportTable("Пороги и количество экстремумов", metric_rows))
        for title, key in (("Минимумы", "minima"), ("Максимумы", "maxima")):
            rows = _table_rows(extremes.get(key))
            if rows:
                tables.append(ReportTable(title, rows))
    return tables


def _analysis_figures(state: Mapping[str, Any], results: dict[str, Any]) -> list[go.Figure]:
    """Готовит графики раздела анализа.

    Args:
        state: Streamlit session state или совместимый mapping.
        results: Нормализованный JSON результата анализа.

    Returns:
        Список Plotly-фигур.
    """

    timeseries = state.get("last_timeseries") or results.get("timeseries")
    linear_trend = _method_payload(results, "linear_trend")
    moving_average = _method_payload(results, "moving_average")
    anomalies = _method_payload(results, "anomalies")
    decomposition = _method_payload(results, "seasonal_decomposition")
    extremes = _method_payload(results, "extremes")
    return [
        build_timeseries_figure(timeseries, title="Исходный временной ряд"),
        build_anomaly_figure(anomalies, title="График аномалий"),
        build_overlay_figure(
            timeseries,
            {"Линейный тренд": linear_trend.get("trend_line") or linear_trend},
            title="Исходный ряд и линейный тренд",
        ),
        build_overlay_figure(timeseries, {"Скользящее среднее": moving_average}, title="Исходный ряд и скользящее среднее"),
        build_decomposition_figure(decomposition),
        build_extremes_figure(timeseries, extremes),
    ]


def _period_metric(rows: list[dict[str, Any]], preferred: str | None) -> str:
    """Выбирает метрику для графика сравнения периодов.

    Args:
        rows: Строки сравнения периодов.
        preferred: Предпочитаемая метрика из session state.

    Returns:
        Имя метрики.
    """

    df = pd.DataFrame(rows)
    if not df.empty and preferred in df.columns:
        return str(preferred)
    for candidate in ("mean", "min", "max", "std", "sum", "value"):
        if not df.empty and candidate in df.columns:
            return candidate
    return preferred or "mean"


def _station_records_from_comparison(state: Mapping[str, Any], records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Дополняет записи сравнения станций координатами из кэша.

    Args:
        state: Streamlit session state или совместимый mapping.
        records: Результаты сравнения станций.

    Returns:
        Записи станций с координатами, если они доступны.
    """

    cached = {str(station_id(station)): station for station in state.get("cached_stations") or []}
    enriched = []
    for record in records:
        key = str(record.get("station_id") or record.get("id") or "")
        station = {**cached.get(key, {}), **record}
        enriched.append(station)
    return enriched or list(cached.values())


def _correlation_pairs_table(payload: dict[str, Any]) -> list[dict[str, Any]]:
    """Преобразует пары корреляций в строки таблицы.

    Args:
        payload: JSON результата корреляционного анализа.

    Returns:
        Таблица коэффициентов корреляции.
    """

    rows = []
    for pair in payload.get("pairs", []) if isinstance(payload, dict) else []:
        rows.append(
            {
                "Параметр X": pair.get("x_parameter_name"),
                "Параметр Y": pair.get("y_parameter_name"),
                "Корреляция": pair.get("correlation"),
                "p-value": pair.get("p_value"),
                "Значима": pair.get("significant"),
                "Наблюдений": pair.get("n"),
            }
        )
    return rows


def _climatogram_table_rows(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Преобразует климатограммы в плоскую таблицу.

    Args:
        items: Результаты климатограмм.

    Returns:
        Строки месячных значений.
    """

    from app.components.charts import climatogram_records_dataframe

    df = climatogram_records_dataframe(items)
    if df.empty:
        return []
    preferred_columns = [
        "station_name",
        "period_label",
        "month",
        "temperature_mean",
        "precipitation_sum",
        "tavg_norm_1995_2024",
        "prcp_norm_1995_2024",
    ]
    labels = {
        "station_name": "Станция",
        "period_label": "Период",
        "month": "Месяц",
        "temperature_mean": "Температура",
        "precipitation_sum": "Осадки",
        "tavg_norm_1995_2024": "Температура норма 1995-2024",
        "prcp_norm_1995_2024": "Осадки норма 1995-2024",
    }
    columns = [column for column in preferred_columns if column in df.columns and df[column].notna().any()]
    return df[columns].rename(columns=labels).to_dict("records") if columns else []


def _build_dashboard_block(state: Mapping[str, Any], include_graphs: bool, include_tables: bool) -> ReportBlock:
    """Создаёт блок отчёта для исследовательской панели.

    Args:
        state: Streamlit session state или совместимый mapping.
        include_graphs: Включать ли графики.
        include_tables: Включать ли таблицы.

    Returns:
        Блок PDF-отчёта.
    """

    stations = _selected_station_records(state)
    return ReportBlock(
        id="dashboard",
        title=_definition("dashboard")["title"],
        description=_definition("dashboard")["description"],
        tables=_dashboard_tables(state) if include_tables else [],
        figures=[build_station_map_figure(stations, title="Карта выбранных метеостанций")] if include_graphs and stations else [],
    )


def _build_analysis_block(state: Mapping[str, Any], include_graphs: bool, include_tables: bool) -> ReportBlock:
    """Создаёт блок отчёта для анализа временного ряда.

    Args:
        state: Streamlit session state или совместимый mapping.
        include_graphs: Включать ли графики.
        include_tables: Включать ли таблицы.

    Returns:
        Блок PDF-отчёта.
    """

    results = result_payload(state.get("last_analysis_result"))
    return ReportBlock(
        id="analysis",
        title=_definition("analysis")["title"],
        description=_definition("analysis")["description"],
        tables=_analysis_tables(results) if include_tables else [],
        figures=_analysis_figures(state, results) if include_graphs else [],
    )


def _build_period_comparison_block(state: Mapping[str, Any], include_graphs: bool, include_tables: bool) -> ReportBlock:
    """Создаёт блок отчёта для сравнения периодов.

    Args:
        state: Streamlit session state или совместимый mapping.
        include_graphs: Включать ли графики.
        include_tables: Включать ли таблицы.

    Returns:
        Блок PDF-отчёта.
    """

    result = state.get("last_period_comparison") or {}
    period_rows = result.get("periods") or []
    differences = result.get("differences") or []
    metric = _period_metric(period_rows, state.get("period_comparison_metric"))
    tables = []
    if include_tables:
        if differences:
            tables.append(ReportTable("Разница относительно базового периода", differences))
        if period_rows:
            tables.append(ReportTable("Таблица сравнения периодов", period_rows))
    figures = []
    if include_graphs and period_rows:
        figures.append(
            build_grouped_bar_chart_figure(
                period_rows,
                x_key="period",
                y_key=metric,
                group_key="station_name",
                title=f"{metric}: значения по периодам",
            )
        )
    return ReportBlock(
        id="period_comparison",
        title=_definition("period_comparison")["title"],
        description=_definition("period_comparison")["description"],
        tables=tables,
        figures=figures,
    )


def _build_station_comparison_block(state: Mapping[str, Any], include_graphs: bool, include_tables: bool) -> ReportBlock:
    """Создаёт блок отчёта для сравнения станций.

    Args:
        state: Streamlit session state или совместимый mapping.
        include_graphs: Включать ли графики.
        include_tables: Включать ли таблицы.

    Returns:
        Блок PDF-отчёта.
    """

    result = state.get("last_station_comparison") or {}
    records = result.get("stations") or result.get("results") or result.get("data") or []
    records = unwrap_records(records) or unwrap_records(result)
    enriched = _station_records_from_comparison(state, records)
    tables = [ReportTable("Результаты сравнения станций", records)] if include_tables and records else []
    figures = []
    if include_graphs:
        series_payloads = state.get("last_station_timeseries") or []
        if series_payloads:
            figures.append(build_multi_timeseries_figure(series_payloads, title="Динамика по выбранным станциям"))
        if records:
            figures.append(build_bar_chart_figure(records, x_key="name", y_key="mean", title="Сравнение станций", color_key="station_id"))
        if enriched:
            figures.append(build_station_map_figure(enriched, title="Карта сравниваемых станций"))
    return ReportBlock(
        id="station_comparison",
        title=_definition("station_comparison")["title"],
        description=_definition("station_comparison")["description"],
        tables=tables,
        figures=figures,
    )


def _build_climatogram_block(state: Mapping[str, Any], include_graphs: bool, include_tables: bool) -> ReportBlock:
    """Создаёт блок отчёта для климатограмм.

    Args:
        state: Streamlit session state или совместимый mapping.
        include_graphs: Включать ли графики.
        include_tables: Включать ли таблицы.

    Returns:
        Блок PDF-отчёта.
    """

    items = state.get("last_climatogram_items") or []
    chart_type = state.get("climatogram_chart_type") or "classic"
    figures = []
    if include_graphs:
        figures = build_climatogram_report_figures(
            items,
            chart_type=chart_type,
            x_axis=state.get("climatogram_scatter_x_axis") or "temperature_mean",
            y_axis=state.get("climatogram_scatter_y_axis") or "precipitation_sum",
            connect_months=bool(state.get("climatogram_scatter_connect_months", True)),
            close_polygon=bool(state.get("climatogram_scatter_close_polygon", True)),
            show_labels=bool(state.get("climatogram_scatter_show_labels", True)),
            overlay_stations=bool(state.get("climatogram_overlay_stations", True)),
            overlay_periods=bool(state.get("climatogram_overlay_periods", False)),
        )
    tables = []
    rows = _climatogram_table_rows(items)
    if include_tables and rows:
        tables.append(ReportTable("Месячные значения климатограмм", rows))
    return ReportBlock(
        id="climatogram",
        title=_definition("climatogram")["title"],
        description=_definition("climatogram")["description"],
        tables=tables,
        figures=figures,
    )


def _build_forecast_block(state: Mapping[str, Any], include_graphs: bool, include_tables: bool) -> ReportBlock:
    """Создаёт блок отчёта для прогнозирования.

    Args:
        state: Streamlit session state или совместимый mapping.
        include_graphs: Включать ли графики.
        include_tables: Включать ли таблицы.

    Returns:
        Блок PDF-отчёта.
    """

    result = state.get("last_forecast") or {}
    forecast_payload = result.get("forecast") or result.get("values") or result
    tables = [ReportTable("Прогнозные значения", _table_rows(forecast_payload))] if include_tables else []
    return ReportBlock(
        id="forecast",
        title=_definition("forecast")["title"],
        description=_definition("forecast")["description"],
        notes=["Прогноз является исследовательским и демонстрационным; точность не гарантируется."],
        tables=[table for table in tables if table.rows],
        figures=[build_forecast_figure(result)] if include_graphs else [],
    )


def _build_correlation_block(state: Mapping[str, Any], include_graphs: bool, include_tables: bool) -> ReportBlock:
    """Создаёт блок отчёта для корреляционного анализа.

    Args:
        state: Streamlit session state или совместимый mapping.
        include_graphs: Включать ли графики.
        include_tables: Включать ли таблицы.

    Returns:
        Блок PDF-отчёта.
    """

    result = state.get("last_correlation_result") or {}
    tables = []
    pair_rows = _correlation_pairs_table(result)
    if include_tables and pair_rows:
        tables.append(ReportTable("Коэффициенты корреляции", pair_rows))
    figures = []
    if include_graphs:
        figures.append(build_correlation_heatmap_figure(result))
        figures.extend(build_correlation_scatter_figures(result))
    return ReportBlock(
        id="correlation",
        title=_definition("correlation")["title"],
        description=_definition("correlation")["description"],
        tables=tables,
        figures=figures,
    )


BLOCK_BUILDERS = {
    "dashboard": _build_dashboard_block,
    "analysis": _build_analysis_block,
    "period_comparison": _build_period_comparison_block,
    "station_comparison": _build_station_comparison_block,
    "climatogram": _build_climatogram_block,
    "forecast": _build_forecast_block,
    "correlation": _build_correlation_block,
}


def build_report_blocks(
    state: Mapping[str, Any],
    selected_section_ids: list[str],
    include_graphs: bool = True,
    include_tables: bool = True,
) -> list[ReportBlock]:
    """Собирает готовые блоки PDF-отчёта.

    Args:
        state: Streamlit session state или совместимый mapping.
        selected_section_ids: Идентификаторы выбранных разделов.
        include_graphs: Включать ли графики.
        include_tables: Включать ли таблицы.

    Returns:
        Список блоков отчёта в выбранном порядке.
    """

    available = set(available_section_ids(state))
    blocks = []
    for section_id in selected_section_ids:
        if section_id not in available:
            continue
        builder = BLOCK_BUILDERS.get(section_id)
        if not builder:
            continue
        blocks.append(builder(state, include_graphs, include_tables))
    return blocks

