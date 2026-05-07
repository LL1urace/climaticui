from __future__ import annotations

import streamlit as st

from klimatika_frontend.api import comparisons
from klimatika_frontend.api.client import ApiError
from klimatika_frontend.components.charts import render_bar_chart
from klimatika_frontend.components.errors import render_api_error
from klimatika_frontend.components.filters import common_filters, date_period
from klimatika_frontend.components.layout import page_title, setup_page
from klimatika_frontend.components.metrics_cards import render_metric_cards
from klimatika_frontend.components.sidebar import render_sidebar
from klimatika_frontend.components.tables import render_json_preview, render_table
from klimatika_frontend.state.session import init_session_state, require_auth
from klimatika_frontend.utils.validators import periods_overlap, validate_period


setup_page("Сравнение периодов")
init_session_state()
require_auth()
render_sidebar()
page_title("Сравнение периодов", "Одна станция и один параметр в двух временных интервалах.")

try:
    with st.sidebar:
        st.header("Параметры")
        filters = common_filters("periods")
        st.subheader("Период 1")
        p1_from, p1_to = date_period("period_1")
        st.subheader("Период 2")
        p2_from, p2_to = date_period("period_2")
        run_clicked = st.button("Сравнить периоды", type="primary", use_container_width=True)
except ApiError as error:
    render_api_error(error)
    st.stop()

if periods_overlap(p1_from, p1_to, p2_from, p2_to):
    st.warning("Выбранные периоды пересекаются. Backend может отклонить такой запрос.")

if run_clicked:
    first_validation = validate_period(p1_from, p1_to)
    second_validation = validate_period(p2_from, p2_to)
    if not first_validation.ok:
        st.error(f"Период 1: {first_validation.message}")
    elif not second_validation.ok:
        st.error(f"Период 2: {second_validation.message}")
    else:
        payload = {
            "station_id": filters["station_id"],
            "parameter_id": filters["parameter_id"],
            "aggregation": filters["aggregation"],
            "period_1": {"date_from": p1_from.isoformat(), "date_to": p1_to.isoformat()},
            "period_2": {"date_from": p2_from.isoformat(), "date_to": p2_to.isoformat()},
        }
        try:
            with st.spinner("Backend сравнивает периоды..."):
                st.session_state["last_period_comparison"] = comparisons.compare_periods(payload)
        except ApiError as error:
            render_api_error(error)

result = st.session_state.get("last_period_comparison")
if not result:
    st.info("Запустите сравнение, чтобы увидеть различия периодов.")
    st.stop()

st.subheader("Разница")
render_metric_cards(result.get("difference") or result.get("diff") or {})
st.subheader("Таблица сравнения")
render_table(result.get("periods") or result.get("results") or result)
st.subheader("График сравнения")
render_bar_chart(result.get("chart_data") or result.get("periods") or result.get("results"), x_key="period", y_key="mean", title="Средние значения по периодам")
render_json_preview(result, "Полный JSON сравнения")

