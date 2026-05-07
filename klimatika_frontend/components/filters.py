"""Shared filters for working pages."""

from __future__ import annotations

from datetime import date
from typing import Any

import streamlit as st

from klimatika_frontend.api import dictionaries, observations
from klimatika_frontend.utils.formatters import parameter_id, parameter_label, station_id, station_label, unwrap_records
from klimatika_frontend.utils.validators import ValidationResult, validate_required_filters


AGGREGATIONS = {
    "raw": "Raw",
    "monthly": "Monthly",
    "yearly": "Yearly",
}


def load_climate_zones() -> list[dict]:
    if st.session_state.get("cached_climate_zones") is None:
        st.session_state["cached_climate_zones"] = unwrap_records(dictionaries.get_climate_zones())
    return st.session_state["cached_climate_zones"]


def load_stations() -> list[dict]:
    if st.session_state.get("cached_stations") is None:
        st.session_state["cached_stations"] = unwrap_records(dictionaries.get_stations())
    return st.session_state["cached_stations"]


def load_parameters() -> list[dict]:
    if st.session_state.get("cached_parameters") is None:
        st.session_state["cached_parameters"] = unwrap_records(dictionaries.get_parameters())
    return st.session_state["cached_parameters"]


def select_station(stations: list[dict], key: str = "station_select") -> Any:
    if not stations:
        st.warning("Backend не вернул список станций.")
        return None
    options = [station_id(station) for station in stations]
    by_id = {station_id(station): station for station in stations}
    default = st.session_state.get("selected_station_id")
    index = options.index(default) if default in options else 0
    return st.selectbox("Метеостанция", options=options, index=index, format_func=lambda item_id: station_label(by_id[item_id]), key=key)


def multiselect_stations(stations: list[dict], key: str = "station_multiselect") -> list[Any]:
    options = [station_id(station) for station in stations]
    by_id = {station_id(station): station for station in stations}
    return st.multiselect("Метеостанции", options=options, format_func=lambda item_id: station_label(by_id[item_id]), key=key)


def select_parameter(parameters: list[dict], key: str = "parameter_select", label: str = "Параметр") -> Any:
    if not parameters:
        st.warning("Backend не вернул список параметров.")
        return None
    options = [parameter_id(parameter) for parameter in parameters]
    by_id = {parameter_id(parameter): parameter for parameter in parameters}
    default = st.session_state.get("selected_parameter_id")
    index = options.index(default) if default in options else 0
    return st.selectbox(label, options=options, index=index, format_func=lambda item_id: parameter_label(by_id[item_id]), key=key)


def select_aggregation(key: str = "aggregation_select") -> str:
    return st.selectbox("Агрегация", options=list(AGGREGATIONS), format_func=lambda item: AGGREGATIONS[item], index=1, key=key)


def date_period(prefix: str = "period", default_start: date | None = None, default_end: date | None = None) -> tuple[date, date]:
    today = date.today()
    start = st.date_input("Начало периода", value=default_start or date(today.year - 5, 1, 1), key=f"{prefix}_date_from")
    end = st.date_input("Конец периода", value=default_end or today, key=f"{prefix}_date_to")
    return start, end


def common_filters(prefix: str = "filters") -> dict[str, Any]:
    stations = load_stations()
    parameters = load_parameters()
    station = select_station(stations, key=f"{prefix}_station")
    parameter = select_parameter(parameters, key=f"{prefix}_parameter")
    aggregation = select_aggregation(key=f"{prefix}_aggregation")
    date_from, date_to = date_period(prefix=prefix)
    return {
        "station_id": station,
        "parameter_id": parameter,
        "date_from": date_from,
        "date_to": date_to,
        "aggregation": aggregation,
        "stations": stations,
        "parameters": parameters,
    }


def analysis_methods() -> list[str]:
    return st.multiselect(
        "Методы анализа",
        options=[
            "basic_statistics",
            "moving_average",
            "linear_trend",
            "climate_norm",
            "anomalies",
            "mann_kendall",
            "seasonal_decomposition",
            "extremes",
        ],
        default=["basic_statistics", "moving_average", "linear_trend", "climate_norm", "anomalies"],
    )


def analysis_options(prefix: str = "analysis") -> dict[str, Any]:
    window = st.number_input("Окно скользящего среднего", min_value=2, max_value=120, value=12, step=1, key=f"{prefix}_ma_window")
    norm_start, norm_end = date_period(prefix=f"{prefix}_norm")
    return {
        "moving_average_window": int(window),
        "window": int(window),
        "norm_period_start": norm_start.isoformat(),
        "norm_period_end": norm_end.isoformat(),
    }


def render_availability(station: Any, parameter: Any) -> None:
    if not station or not parameter:
        return
    try:
        availability = observations.get_availability(station, parameter)
    except Exception:
        return
    if not isinstance(availability, dict):
        return
    date_min = availability.get("date_min") or availability.get("date_from")
    date_max = availability.get("date_max") or availability.get("date_to")
    count = availability.get("count")
    if date_min or date_max or count:
        st.caption(f"Доступность: {date_min or '?'} - {date_max or '?'}; наблюдений: {count or '?'}")


def validate_common_filters(filters: dict[str, Any]) -> ValidationResult:
    return validate_required_filters(filters.get("station_id"), filters.get("parameter_id"), filters.get("date_from"), filters.get("date_to"))
