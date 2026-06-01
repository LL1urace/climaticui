from __future__ import annotations

import sys
from pathlib import Path

import streamlit as st

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.api import analysis
from app.api.client import ApiError
from app.components.errors import render_api_error
from app.components.layout import page_title, render_home_button, setup_page
from app.components.sidebar import render_sidebar
from app.components.tables import render_json_preview, render_table
from app.state.session import init_session_state, remember_analysis, require_auth
from app.utils.formatters import unwrap_records


setup_page("История анализов")
init_session_state()
require_auth()
render_sidebar()
page_title("История анализов", "История текущего пользователя хранится и фильтруется backend.")
render_home_button()

try:
    with st.spinner("Загружаю историю..."):
        history_response = analysis.get_history()
except ApiError as error:
    render_api_error(error)
    st.stop()

runs = unwrap_records(history_response)
if not runs:
    st.info("История анализов пуста.")
    st.stop()

statuses = sorted({str(run.get("status")) for run in runs if run.get("status")})
with st.container(border=True, key="history_parameters"):
    st.subheader("Параметры истории")
    selected_status = st.selectbox("Статус", ["Все"] + statuses)
    visible_runs = [run for run in runs if selected_status == "Все" or str(run.get("status")) == selected_status]
    run_ids = [run.get("analysis_run_id") or run.get("id") for run in visible_runs]
    run_ids = [run_id for run_id in run_ids if run_id is not None]
    selected_run_id = st.selectbox("Открыть анализ", run_ids) if run_ids else None
    open_clicked = st.button("Открыть результат", type="primary", use_container_width=True, disabled=not run_ids)

render_table(visible_runs)

if open_clicked and selected_run_id is not None:
    try:
        with st.spinner("Загружаю результат анализа..."):
            result = analysis.get_analysis_result(selected_run_id)
            remember_analysis(result)
            st.session_state["opened_analysis_result"] = result
    except ApiError as error:
        render_api_error(error)

opened = st.session_state.get("opened_analysis_result")
if opened:
    st.subheader("Результат анализа")
    render_json_preview(opened, "JSON результата")
    if st.button("Использовать для отчёта"):
        remember_analysis(opened)
        st.success("Анализ сохранён как последний выбранный.")

