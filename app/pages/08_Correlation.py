from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

import streamlit as st

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.api import analysis
from app.api.client import ApiError
from app.components.charts import render_correlation_heatmap, render_correlation_scatter
from app.components.errors import render_api_error
from app.components.filters import date_period, load_parameters, load_stations, select_aggregation, select_station
from app.components.layout import page_title, render_home_button, setup_page
from app.components.sidebar import render_sidebar
from app.components.tables import render_json_preview, render_table
from app.state.session import init_session_state, remember_selection, require_auth
from app.utils.formatters import parameter_id, parameter_label
from app.utils.validators import validate_period


CORRELATION_METHODS = {
    "pearson": "Пирсон",
    "spearman": "Спирмен",
}


def _select_parameters(parameters: list[dict]) -> list[Any]:
    """Отображает выбор нескольких климатических параметров.

    Args:
        parameters: Список параметров из backend API.

    Returns:
        Список идентификаторов выбранных параметров.
    """

    options = [parameter_id(parameter) for parameter in parameters]
    by_id = {parameter_id(parameter): parameter for parameter in parameters}
    default = options[: min(3, len(options))]
    return st.multiselect(
        "Параметры",
        options=options,
        default=default,
        format_func=lambda item_id: parameter_label(by_id[item_id]),
        key="correlation_parameters",
    )


def _correlation_signature(
    station: Any,
    parameter_ids: list[Any],
    date_from: Any,
    date_to: Any,
    aggregation: str,
    method: str,
) -> tuple:
    """Формирует подпись текущих параметров корреляционного анализа.

    Args:
        station: Идентификатор станции.
        parameter_ids: Выбранные параметры.
        date_from: Начальная дата периода.
        date_to: Конечная дата периода.
        aggregation: Код агрегации.
        method: Метод корреляции.

    Returns:
        Hashable-подпись входных параметров.
    """

    return (
        str(station),
        tuple(str(item) for item in parameter_ids),
        date_from.isoformat() if date_from else "",
        date_to.isoformat() if date_to else "",
        aggregation,
        method,
    )


def _pairs_table(payload: dict) -> list[dict]:
    """Преобразует пары корреляций в строки таблицы.

    Args:
        payload: JSON результата корреляционного анализа.

    Returns:
        Список строк с коэффициентами корреляции.
    """

    rows = []
    for pair in (payload.get("pairs", []) if isinstance(payload, dict) else []):
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


setup_page("Корреляционный анализ")
init_session_state()
require_auth()
render_sidebar()
page_title("Корреляционный анализ", "Оценка связи между климатическими параметрами одной метеостанции.")
render_home_button()

try:
    with st.sidebar:
        st.header("Параметры корреляции")
        stations = load_stations()
        parameters = load_parameters()
        station = select_station(stations, key="correlation_station")
        selected_parameter_ids = _select_parameters(parameters)
        aggregation = select_aggregation("correlation_aggregation")
        method = st.selectbox(
            "Метод",
            options=list(CORRELATION_METHODS),
            format_func=lambda item: CORRELATION_METHODS[item],
            key="correlation_method",
        )
        date_from, date_to = date_period("correlation_period")
        remember_selection(station_id=station, parameter_id=selected_parameter_ids[0] if selected_parameter_ids else None)
        run_clicked = st.button("Рассчитать корреляции", type="primary", use_container_width=True)
except ApiError as error:
    render_api_error(error)
    st.stop()

if run_clicked:
    period_validation = validate_period(date_from, date_to)
    if not station:
        st.error("Выберите метеостанцию.")
    elif len(selected_parameter_ids) < 2:
        st.error("Выберите минимум два параметра.")
    elif not period_validation.ok:
        st.error(period_validation.message)
    else:
        payload = {
            "station_id": station,
            "parameter_ids": selected_parameter_ids,
            "date_from": date_from.isoformat(),
            "date_to": date_to.isoformat(),
            "aggregation": aggregation,
            "method": method,
        }
        try:
            with st.spinner("Backend рассчитывает корреляции..."):
                result = analysis.run_correlation(payload)
                st.session_state["last_correlation_result"] = result
                st.session_state["last_correlation_signature"] = _correlation_signature(
                    station,
                    selected_parameter_ids,
                    date_from,
                    date_to,
                    aggregation,
                    method,
                )
        except ApiError as error:
            render_api_error(error)

current_signature = _correlation_signature(station, selected_parameter_ids, date_from, date_to, aggregation, method)
stored_signature = st.session_state.get("last_correlation_signature")
result = st.session_state.get("last_correlation_result")
if result and stored_signature != current_signature:
    st.info("Параметры корреляции изменились. Нажмите «Рассчитать корреляции», чтобы обновить графики.")
    result = None

if not result:
    st.info("Выберите станцию, минимум два параметра и запустите корреляционный анализ.")
    st.stop()

st.subheader("Матрица корреляций")
render_correlation_heatmap(result)

st.subheader("Таблица коэффициентов")
render_table(_pairs_table(result), empty_message="Коэффициенты корреляции отсутствуют.")

render_correlation_scatter(result)
render_json_preview(result, "Полный JSON корреляционного анализа")
