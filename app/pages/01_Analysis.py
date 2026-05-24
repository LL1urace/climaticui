from __future__ import annotations

import sys
from pathlib import Path

import streamlit as st

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.api import analysis, observations
from app.api.client import ApiError
from app.components.charts import (
    render_anomaly_chart,
    render_decomposition_chart,
    render_extremes_chart,
    render_overlay_chart,
    render_timeseries_chart,
)
from app.components.errors import render_api_error, render_method_errors
from app.components.filters import analysis_methods, analysis_options, common_filters, render_availability, validate_common_filters
from app.components.layout import page_title, render_home_button, setup_page
from app.components.metrics_cards import render_metric_cards
from app.components.sidebar import render_sidebar
from app.components.tables import render_json_preview, render_table
from app.state.session import init_session_state, remember_analysis, remember_selection, require_auth
from app.utils.formatters import result_payload


def method_payload(results: dict, name: str) -> dict:
    """Возвращает результат конкретного метода анализа из общего JSON.

    Args:
        results: Словарь результатов анализа, полученный от backend API.
        name: Код метода анализа.

    Returns:
        Словарь payload метода или пустой словарь, если данных нет.
    """

    payload = results.get(name)
    if isinstance(payload, dict) and isinstance(payload.get("result"), dict):
        return payload["result"]
    return payload if isinstance(payload, dict) else {}


def scalar_metrics(payload: dict) -> dict:
    """Возвращает только скалярные значения результата метода.

    Args:
        payload: JSON результата метода анализа.

    Returns:
        Словарь без вложенных списков и словарей.
    """

    return {
        key: value
        for key, value in payload.items()
        if key != "status" and not isinstance(value, (dict, list))
    }


setup_page("Анализ")
init_session_state()
require_auth()
render_sidebar()
page_title("Анализ временного ряда", "Выберите станцию, параметр, период и методы. Расчёты выполняет backend.")
render_home_button()

try:
    with st.sidebar:
        st.header("Параметры анализа")
        filters = common_filters("analysis")
        remember_selection(filters["station_id"], filters["parameter_id"])
        render_availability(filters["station_id"], filters["parameter_id"])
        methods = analysis_methods()
        options = analysis_options("analysis")
        run_clicked = st.button("Запустить анализ", type="primary", use_container_width=True)
except ApiError as error:
    render_api_error(error)
    st.stop()

if run_clicked:
    validation = validate_common_filters(filters)
    if not validation.ok:
        st.error(validation.message)
    elif not methods:
        st.error("Выберите хотя бы один метод анализа.")
    else:
        payload = {
            "station_id": filters["station_id"],
            "parameter_id": filters["parameter_id"],
            "date_from": filters["date_from"].isoformat(),
            "date_to": filters["date_to"].isoformat(),
            "aggregation": filters["aggregation"],
            "methods": methods,
            "options": options,
        }
        try:
            with st.spinner("Запрашиваю временной ряд и запускаю анализ..."):
                st.session_state["last_timeseries"] = observations.get_timeseries(
                    filters["station_id"],
                    filters["parameter_id"],
                    payload["date_from"],
                    payload["date_to"],
                    filters["aggregation"],
                )
        except ApiError as error:
            render_api_error(error)
            st.session_state["last_timeseries"] = None

        try:
            with st.spinner("Backend выполняет анализ..."):
                result = analysis.run_analysis(payload)
                remember_analysis(result)
                st.success("Анализ выполнен.")
        except ApiError as error:
            render_api_error(error)

result = st.session_state.get("last_analysis_result")
if not result:
    st.info("Запустите анализ, чтобы увидеть метрики, графики и таблицы.")
    st.stop()

results = result_payload(result)
timeseries = st.session_state.get("last_timeseries") or result.get("timeseries") or results.get("timeseries")

st.subheader("Временной ряд")
render_timeseries_chart(timeseries, title="Исходный временной ряд")

st.subheader("Базовая статистика")
basic_statistics = method_payload(results, "basic_statistics")
render_metric_cards(basic_statistics.get("metrics") if "metrics" in basic_statistics else basic_statistics)
render_table(basic_statistics, empty_message="Базовая статистика отсутствует.")

st.subheader("Климатические нормы и аномалии")
climate_norm = method_payload(results, "climate_norm")
anomalies = method_payload(results, "anomalies")
norm_col, anomaly_col = st.columns([0.42, 0.58])
with norm_col:
    render_table(climate_norm, empty_message="Климатическая норма отсутствует.")
with anomaly_col:
    render_metric_cards(scalar_metrics(anomalies), columns=2)
render_anomaly_chart(timeseries, anomalies, title="График аномалий")

st.subheader("Тренды")
linear_trend = method_payload(results, "linear_trend")
mann_kendall = method_payload(results, "mann_kendall")
render_overlay_chart(
    timeseries,
    {"Линейный тренд": linear_trend.get("trend_line") or linear_trend},
    title="Исходный ряд и линейный тренд",
)
trend_cols = st.columns(2)
with trend_cols[0]:
    st.markdown("**Линейная регрессия**")
    render_metric_cards(scalar_metrics(linear_trend), columns=3)
with trend_cols[1]:
    st.markdown("**Тест Манна-Кендалла**")
    render_metric_cards(scalar_metrics(mann_kendall), columns=3)
render_table(mann_kendall, empty_message="Результат теста Манна-Кендалла отсутствует.")

st.subheader("Сглаживание")
moving_average = method_payload(results, "moving_average")
render_overlay_chart(
    timeseries,
    {"Скользящее среднее": moving_average},
    title="Исходный ряд и скользящее среднее",
)

st.subheader("Сезонная декомпозиция")
render_decomposition_chart(method_payload(results, "seasonal_decomposition"))

st.subheader("Экстремумы")
extremes = method_payload(results, "extremes")
thresholds = extremes.get("thresholds") if isinstance(extremes.get("thresholds"), dict) else {}
counts = extremes.get("counts") if isinstance(extremes.get("counts"), dict) else {}
extreme_metrics = {**(thresholds or {}), **(counts or {})}
if extremes.get("top_n") is not None:
    extreme_metrics["top_n"] = extremes.get("top_n")
render_metric_cards(extreme_metrics, columns=5)
render_extremes_chart(timeseries, extremes)
extreme_cols = st.columns(2)
with extreme_cols[0]:
    st.markdown("**Минимумы**")
    render_table(extremes.get("minima") if isinstance(extremes, dict) else None, empty_message="Минимумы отсутствуют.")
with extreme_cols[1]:
    st.markdown("**Максимумы**")
    render_table(extremes.get("maxima") if isinstance(extremes, dict) else None, empty_message="Максимумы отсутствуют.")

render_method_errors(results)
render_json_preview(result, "Полный JSON результата")
