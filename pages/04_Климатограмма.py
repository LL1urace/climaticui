from __future__ import annotations

import streamlit as st

from klimatika_frontend.api import analysis
from klimatika_frontend.api.client import ApiError
from klimatika_frontend.components.charts import render_climatogram
from klimatika_frontend.components.errors import render_api_error
from klimatika_frontend.components.filters import date_period, load_parameters, load_stations, select_parameter, select_station
from klimatika_frontend.components.layout import page_title, setup_page
from klimatika_frontend.components.sidebar import render_sidebar
from klimatika_frontend.components.tables import render_json_preview, render_table
from klimatika_frontend.state.session import init_session_state, require_auth
from klimatika_frontend.utils.validators import validate_period


setup_page("Климатограмма")
init_session_state()
require_auth()
render_sidebar()
page_title("Климатограмма", "Температура линией и осадки столбцами по месяцам.")

try:
    with st.sidebar:
        stations = load_stations()
        parameters = load_parameters()
        station = select_station(stations, "climatogram_station")
        date_from, date_to = date_period("climatogram")
        temperature_parameter = select_parameter(parameters, "climatogram_temp", "Параметр температуры")
        precipitation_parameter = select_parameter(parameters, "climatogram_precip", "Параметр осадков")
        run_clicked = st.button("Построить климатограмму", type="primary", use_container_width=True)
except ApiError as error:
    render_api_error(error)
    st.stop()

if run_clicked:
    validation = validate_period(date_from, date_to)
    if not validation.ok:
        st.error(validation.message)
    else:
        payload = {
            "station_id": station,
            "date_from": date_from.isoformat(),
            "date_to": date_to.isoformat(),
            "temperature_parameter_id": temperature_parameter,
            "precipitation_parameter_id": precipitation_parameter,
        }
        try:
            with st.spinner("Backend строит климатограмму..."):
                st.session_state["last_climatogram"] = analysis.run_climatogram(payload)
        except ApiError as error:
            render_api_error(error)

result = st.session_state.get("last_climatogram")
if not result:
    st.info("Выберите станцию, параметры и период.")
    st.stop()

render_climatogram(result)
render_table(result.get("months") or result.get("values") or result)
render_json_preview(result, "Полный JSON климатограммы")

