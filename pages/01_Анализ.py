from __future__ import annotations

import streamlit as st

from klimatika_frontend.api import analysis, observations
from klimatika_frontend.api.client import ApiError
from klimatika_frontend.components.charts import render_overlay_chart, render_timeseries_chart
from klimatika_frontend.components.errors import render_api_error, render_method_errors
from klimatika_frontend.components.filters import analysis_methods, analysis_options, common_filters, render_availability, validate_common_filters
from klimatika_frontend.components.layout import page_title, setup_page
from klimatika_frontend.components.metrics_cards import render_metric_cards
from klimatika_frontend.components.sidebar import render_sidebar
from klimatika_frontend.components.tables import render_json_preview, render_table
from klimatika_frontend.state.session import init_session_state, remember_analysis, remember_selection, require_auth
from klimatika_frontend.utils.formatters import result_payload


def method_payload(results: dict, name: str) -> dict:
    payload = results.get(name)
    if isinstance(payload, dict) and isinstance(payload.get("result"), dict):
        return payload["result"]
    return payload if isinstance(payload, dict) else {}


setup_page("Анализ")
init_session_state()
require_auth()
render_sidebar()
page_title("Анализ временного ряда", "Выберите станцию, параметр, период и методы. Расчёты выполняет backend.")

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

st.subheader("Ключевые результаты")
basic_statistics = method_payload(results, "basic_statistics")
render_metric_cards(basic_statistics.get("metrics") if "metrics" in basic_statistics else basic_statistics)
render_table(basic_statistics, empty_message="Базовая статистика отсутствует.")

overlays = {
    "Скользящее среднее": method_payload(results, "moving_average"),
    "Линейный тренд": method_payload(results, "linear_trend").get("trend_line") or method_payload(results, "linear_trend"),
    "Аномалии": method_payload(results, "anomalies"),
}
st.subheader("Графики методов")
render_overlay_chart(timeseries, overlays, title="Ряд и результаты анализа")

st.subheader("Климатическая норма")
render_table(method_payload(results, "climate_norm"), empty_message="Климатическая норма отсутствует.")

render_method_errors(results)
render_json_preview(result, "Полный JSON результата")
