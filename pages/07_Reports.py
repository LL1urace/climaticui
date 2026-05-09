from __future__ import annotations

import json

import streamlit as st

from klimatika_frontend.api import analysis, reports
from klimatika_frontend.api.client import ApiError
from klimatika_frontend.components.errors import render_api_error
from klimatika_frontend.components.layout import page_title, render_home_button, setup_page
from klimatika_frontend.components.sidebar import render_sidebar
from klimatika_frontend.components.tables import render_json_preview, render_table
from klimatika_frontend.state.session import init_session_state, require_auth
from klimatika_frontend.utils.formatters import unwrap_records


setup_page("Отчёты")
init_session_state()
require_auth()
render_sidebar()
page_title("Отчёты", "Формирование и скачивание отчётов выполняет backend.")
render_home_button()

last_run_id = st.session_state.get("last_analysis_run_id")
selected_run_id = last_run_id

try:
    history_response = analysis.get_history()
    runs = unwrap_records(history_response)
except ApiError:
    runs = []

if runs:
    run_ids = [run.get("analysis_run_id") or run.get("id") for run in runs]
    run_ids = [run_id for run_id in run_ids if run_id is not None]
    if run_ids:
        default_index = run_ids.index(last_run_id) if last_run_id in run_ids else 0
        selected_run_id = st.selectbox("Analysis run", run_ids, index=default_index)
        render_table(runs)
elif selected_run_id:
    st.info(f"Будет использован последний анализ: {selected_run_id}")
else:
    st.info("Сначала запустите анализ или выберите анализ из истории.")

if selected_run_id and st.button("Сформировать отчёт", type="primary"):
    try:
        with st.spinner("Backend формирует отчёт..."):
            report = reports.create_report(selected_run_id)
            st.session_state["last_report"] = report
    except ApiError as error:
        render_api_error(error)

report = st.session_state.get("last_report")
if not report:
    st.stop()

st.subheader("Отчёт")
render_json_preview(report, "Metadata отчёта")
report_id = report.get("report_id") or report.get("id")
if report_id:
    try:
        content = reports.download_report(report_id)
        st.download_button(
            "Скачать отчёт",
            data=content,
            file_name=f"klimatika_report_{report_id}.json",
            mime="application/json",
            use_container_width=True,
        )
        try:
            st.json(json.loads(content.decode("utf-8")))
        except Exception:
            st.caption("Отчёт скачан как бинарный файл.")
    except ApiError as error:
        render_api_error(error)
