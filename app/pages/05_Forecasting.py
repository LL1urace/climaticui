from __future__ import annotations

import sys
from pathlib import Path

import streamlit as st

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.api import forecasts
from app.api.client import ApiError
from app.components.charts import render_timeseries_chart
from app.components.errors import render_api_error
from app.components.filters import common_filters, validate_common_filters
from app.components.layout import page_title, render_home_button, setup_page
from app.components.sidebar import render_sidebar
from app.components.tables import render_json_preview, render_table
from app.state.session import init_session_state, require_auth


setup_page("Прогнозирование")
init_session_state()
require_auth()
render_sidebar()
page_title("Прогнозирование", "Исследовательский прогноз, рассчитанный backend.")
render_home_button()
st.warning("Прогноз является исследовательским и демонстрационным; точность не гарантируется.")

try:
    with st.sidebar:
        filters = common_filters("forecast")
        model = st.selectbox("Модель", ["linear_trend", "moving_average", "seasonal_naive"])
        horizon = st.number_input("Горизонт", min_value=1, max_value=120, value=12, step=1)
        horizon_unit = st.selectbox("Единица горизонта", ["days", "months", "years"], index=1)
        run_clicked = st.button("Запустить прогноз", type="primary", use_container_width=True)
except ApiError as error:
    render_api_error(error)
    st.stop()

if run_clicked:
    validation = validate_common_filters(filters)
    if not validation.ok:
        st.error(validation.message)
    else:
        payload = {
            "station_id": filters["station_id"],
            "parameter_id": filters["parameter_id"],
            "date_from": filters["date_from"].isoformat(),
            "date_to": filters["date_to"].isoformat(),
            "aggregation": filters["aggregation"],
            "model": model,
            "horizon": int(horizon),
            "horizon_unit": horizon_unit,
        }
        try:
            with st.spinner("Backend выполняет прогноз..."):
                st.session_state["last_forecast"] = forecasts.run_forecast(payload)
        except ApiError as error:
            render_api_error(error)

result = st.session_state.get("last_forecast")
if not result:
    st.info("Выберите параметры и запустите прогноз.")
    st.stop()

render_timeseries_chart(result.get("forecast") or result.get("values") or result, title="Прогнозные значения")
render_table(result.get("forecast") or result.get("values") or result)
render_json_preview(result, "Полный JSON прогноза")

