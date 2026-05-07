from __future__ import annotations

import streamlit as st

from klimatika_frontend.api import comparisons
from klimatika_frontend.api.client import ApiError
from klimatika_frontend.components.charts import render_bar_chart
from klimatika_frontend.components.errors import render_api_error
from klimatika_frontend.components.filters import date_period, load_parameters, load_stations, multiselect_stations, select_aggregation, select_parameter
from klimatika_frontend.components.layout import page_title, setup_page
from klimatika_frontend.components.maps import render_stations_map
from klimatika_frontend.components.sidebar import render_sidebar
from klimatika_frontend.components.tables import render_json_preview, render_table
from klimatika_frontend.state.session import init_session_state, require_auth
from klimatika_frontend.utils.formatters import station_id
from klimatika_frontend.utils.validators import validate_min_stations, validate_period


setup_page("Сравнение станций")
init_session_state()
require_auth()
render_sidebar()
page_title("Сравнение станций", "Несколько метеостанций по одному параметру и одной метрике.")

try:
    with st.sidebar:
        stations = load_stations()
        parameters = load_parameters()
        selected_stations = multiselect_stations(stations, "compare_stations")
        parameter = select_parameter(parameters, key="compare_station_parameter")
        aggregation = select_aggregation("compare_station_aggregation")
        metric = st.selectbox("Метрика", ["mean", "min", "max", "std", "sum"])
        date_from, date_to = date_period("compare_stations_period")
        run_clicked = st.button("Сравнить станции", type="primary", use_container_width=True)
except ApiError as error:
    render_api_error(error)
    st.stop()

if run_clicked:
    station_validation = validate_min_stations(selected_stations)
    period_validation = validate_period(date_from, date_to)
    if not station_validation.ok:
        st.error(station_validation.message)
    elif not parameter:
        st.error("Выберите параметр.")
    elif not period_validation.ok:
        st.error(period_validation.message)
    else:
        payload = {
            "station_ids": selected_stations,
            "parameter_id": parameter,
            "date_from": date_from.isoformat(),
            "date_to": date_to.isoformat(),
            "aggregation": aggregation,
            "metric": metric,
        }
        try:
            with st.spinner("Backend сравнивает станции..."):
                st.session_state["last_station_comparison"] = comparisons.compare_stations(payload)
        except ApiError as error:
            render_api_error(error)

result = st.session_state.get("last_station_comparison")
if not result:
    st.info("Выберите минимум две станции и запустите сравнение.")
    st.stop()

records = result.get("stations") or result.get("results") or result.get("data")
st.subheader("Результаты")
render_table(records or result)
st.subheader("График")
render_bar_chart(records or result, x_key="name", y_key=metric, title="Сравнение станций")

selected_station_records = [station for station in stations if station_id(station) in selected_stations]
st.subheader("Карта станций")
render_stations_map(records or selected_station_records, value_key=metric)
render_json_preview(result, "Полный JSON сравнения")

