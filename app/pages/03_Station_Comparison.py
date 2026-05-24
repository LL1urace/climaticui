from __future__ import annotations

import sys
from pathlib import Path

import streamlit as st

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.api import comparisons, observations
from app.api.client import ApiError
from app.components.charts import render_bar_chart, render_multi_timeseries_chart
from app.components.errors import render_api_error
from app.components.filters import date_period, load_parameters, load_stations, multiselect_stations, select_aggregation, select_parameter
from app.components.layout import page_title, render_home_button, setup_page
from app.components.maps import render_stations_map
from app.components.sidebar import render_sidebar
from app.components.tables import render_json_preview, render_table
from app.state.session import init_session_state, require_auth
from app.utils.formatters import station_id
from app.utils.validators import validate_min_stations, validate_period


DEFAULT_STATION_COLORS = [
    "#0d64d8",
    "#17b6d6",
    "#f59e0b",
    "#16a34a",
    "#dc2626",
    "#7c3aed",
    "#0891b2",
    "#be123c",
]


def _fallback_station(station_identifier: object) -> dict:
    """Создаёт минимальную запись станции для подписи в UI.

    Args:
        station_identifier: Идентификатор станции.

    Returns:
        Словарь с названием и идентификатором станции.
    """

    return {"id": station_identifier, "name": f"Станция {station_identifier}"}


def _station_lookup(stations: list[dict]) -> dict[object, dict]:
    """Возвращает справочник станций по идентификатору.

    Args:
        stations: Список станций из backend API.

    Returns:
        Словарь station_id -> запись станции.
    """

    return {station_id(station): station for station in stations}


def _station_color_key(station_identifier: object) -> str:
    """Формирует ключ Streamlit для color picker станции.

    Args:
        station_identifier: Идентификатор станции.

    Returns:
        Уникальный ключ color picker.
    """

    return f"compare_station_color_{station_identifier}"


def _render_station_palette(stations: list[dict], selected_station_ids: list[object]) -> dict[object, str]:
    """Отображает палитру цветов для выбранных станций.

    Args:
        stations: Список станций из backend API.
        selected_station_ids: Идентификаторы выбранных станций.

    Returns:
        Сопоставление station_id и hex-цвета.
    """

    if not selected_station_ids:
        return {}

    by_id = _station_lookup(stations)
    colors: dict[object, str] = {}
    with st.expander("Палитра станций", expanded=False):
        st.caption("Цвета применяются к линейному графику и диаграмме сравнения.")
        for index, current_station_id in enumerate(selected_station_ids):
            station = by_id.get(current_station_id, _fallback_station(current_station_id))
            default_color = DEFAULT_STATION_COLORS[index % len(DEFAULT_STATION_COLORS)]
            color = st.color_picker(
                station.get("name") or f"Станция {current_station_id}",
                value=st.session_state.get(_station_color_key(current_station_id), default_color),
                key=_station_color_key(current_station_id),
            )
            colors[current_station_id] = color
            colors[str(current_station_id)] = color
    return colors


def _load_station_timeseries(
    stations: list[dict],
    selected_station_ids: list[object],
    parameter: object,
    date_from: object,
    date_to: object,
    aggregation: str,
) -> list[dict]:
    """Загружает временные ряды для выбранных станций.

    Args:
        stations: Список станций из backend API.
        selected_station_ids: Идентификаторы выбранных станций.
        parameter: Идентификатор климатического параметра.
        date_from: Начало периода.
        date_to: Конец периода.
        aggregation: Тип агрегации.

    Returns:
        Список рядов с подписями станций.
    """

    by_id = _station_lookup(stations)
    series_by_station = []
    for current_station_id in selected_station_ids:
        station = by_id.get(current_station_id, _fallback_station(current_station_id))
        series_by_station.append(
            {
                "station_id": current_station_id,
                "label": station.get("name") or f"Станция {current_station_id}",
                "series": observations.get_timeseries(
                    current_station_id,
                    parameter,
                    date_from.isoformat(),
                    date_to.isoformat(),
                    aggregation,
                ),
            }
        )
    return series_by_station


setup_page("Сравнение станций")
init_session_state()
require_auth()
render_sidebar()
page_title("Сравнение станций", "Несколько метеостанций по одному параметру и одной метрике.")
render_home_button()

try:
    with st.sidebar:
        stations = load_stations()
        parameters = load_parameters()
        selected_stations = multiselect_stations(stations, "compare_stations")
        station_colors = _render_station_palette(stations, selected_stations)
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
            with st.spinner("Backend сравнивает станции и загружает временные ряды..."):
                st.session_state["last_station_comparison"] = comparisons.compare_stations(payload)
                st.session_state["last_station_timeseries"] = _load_station_timeseries(
                    stations,
                    selected_stations,
                    parameter,
                    date_from,
                    date_to,
                    aggregation,
                )
        except ApiError as error:
            render_api_error(error)

result = st.session_state.get("last_station_comparison")
if not result:
    st.info("Выберите минимум две станции и запустите сравнение.")
    st.stop()

records = result.get("stations") or result.get("results") or result.get("data")
st.subheader("Результаты")
render_table(records or result)

st.subheader("Изменение показателя")
render_multi_timeseries_chart(
    st.session_state.get("last_station_timeseries") or [],
    title="Динамика по выбранным станциям",
    color_map=station_colors,
)

st.subheader("График")
render_bar_chart(
    records or result,
    x_key="name",
    y_key=metric,
    title="Сравнение станций",
    color_key="station_id",
    color_map=station_colors,
)

selected_station_records = [station for station in stations if station_id(station) in selected_stations]
st.subheader("Карта станций")
render_stations_map(records or selected_station_records, value_key=metric)
render_json_preview(result, "Полный JSON сравнения")

