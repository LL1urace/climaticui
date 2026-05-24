"""Shared filters for working pages."""

from __future__ import annotations

from datetime import date
from typing import Any

import streamlit as st

from app.api import dictionaries, observations
from app.utils.formatters import parameter_id, parameter_label, station_id, station_label, unwrap_records
from app.utils.validators import ValidationResult, validate_required_filters


AGGREGATIONS = {
    "raw": "Raw",
    "monthly": "Monthly",
    "yearly": "Yearly",
}

ANALYSIS_METHOD_LABELS = {
    "basic_statistics": "Агрегация и базовая статистика",
    "moving_average": "Сглаживание: скользящее среднее",
    "linear_trend": "Линейный тренд",
    "climate_norm": "Климатические нормы",
    "anomalies": "Аномалии",
    "mann_kendall": "Тест Манна-Кендалла",
    "seasonal_decomposition": "Сезонная декомпозиция",
    "extremes": "Экстремумы",
}


def load_climate_zones() -> list[dict]:
    """Загружает и кэширует климатические зоны.

    Returns:
        Список климатических зон.

    Raises:
        ApiError: Если backend вернул ошибку загрузки справочника.
    """

    if st.session_state.get("cached_climate_zones") is None:
        st.session_state["cached_climate_zones"] = unwrap_records(dictionaries.get_climate_zones())
    return st.session_state["cached_climate_zones"]


def load_stations() -> list[dict]:
    """Загружает и кэширует список метеостанций.

    Returns:
        Список метеостанций.

    Raises:
        ApiError: Если backend вернул ошибку загрузки справочника.
    """

    if st.session_state.get("cached_stations") is None:
        st.session_state["cached_stations"] = unwrap_records(dictionaries.get_stations())
    return st.session_state["cached_stations"]


def load_parameters() -> list[dict]:
    """Загружает и кэширует список климатических параметров.

    Returns:
        Список климатических параметров.

    Raises:
        ApiError: Если backend вернул ошибку загрузки справочника.
    """

    if st.session_state.get("cached_parameters") is None:
        st.session_state["cached_parameters"] = unwrap_records(dictionaries.get_parameters())
    return st.session_state["cached_parameters"]


def select_station(stations: list[dict], key: str = "station_select") -> Any:
    """Отображает selectbox выбора одной метеостанции.

    Args:
        stations: Список станций из backend API.
        key: Уникальный ключ Streamlit-виджета.

    Returns:
        Идентификатор выбранной станции или None.
    """

    if not stations:
        st.warning("Backend не вернул список станций.")
        return None
    options = [station_id(station) for station in stations]
    by_id = {station_id(station): station for station in stations}
    default = st.session_state.get("selected_station_id")
    index = options.index(default) if default in options else 0
    return st.selectbox("Метеостанция", options=options, index=index, format_func=lambda item_id: station_label(by_id[item_id]), key=key)


def multiselect_stations(stations: list[dict], key: str = "station_multiselect", default_ids: list[Any] | None = None) -> list[Any]:
    """Отображает multiselect выбора нескольких метеостанций.

    Args:
        stations: Список станций из backend API.
        key: Уникальный ключ Streamlit-виджета.
        default_ids: Идентификаторы станций, выбранные по умолчанию.

    Returns:
        Список идентификаторов выбранных станций.
    """

    options = [station_id(station) for station in stations]
    by_id = {station_id(station): station for station in stations}
    stored_default = default_ids if default_ids is not None else st.session_state.get("dashboard_station_ids") or []
    default = [item_id for item_id in stored_default if item_id in options]
    return st.multiselect("Метеостанции", options=options, default=default, format_func=lambda item_id: station_label(by_id[item_id]), key=key)


def select_parameter(parameters: list[dict], key: str = "parameter_select", label: str = "Параметр") -> Any:
    """Отображает selectbox выбора климатического параметра.

    Args:
        parameters: Список параметров из backend API.
        key: Уникальный ключ Streamlit-виджета.
        label: Подпись поля выбора.

    Returns:
        Идентификатор выбранного параметра или None.
    """

    if not parameters:
        st.warning("Backend не вернул список параметров.")
        return None
    options = [parameter_id(parameter) for parameter in parameters]
    by_id = {parameter_id(parameter): parameter for parameter in parameters}
    default = st.session_state.get("selected_parameter_id")
    index = options.index(default) if default in options else 0
    return st.selectbox(label, options=options, index=index, format_func=lambda item_id: parameter_label(by_id[item_id]), key=key)


def select_aggregation(key: str = "aggregation_select") -> str:
    """Отображает выбор типа агрегации временного ряда.

    Args:
        key: Уникальный ключ Streamlit-виджета.

    Returns:
        Код выбранной агрегации.
    """

    options = list(AGGREGATIONS)
    default = st.session_state.get("dashboard_aggregation")
    index = options.index(default) if default in options else 1
    return st.selectbox("Агрегация", options=options, format_func=lambda item: AGGREGATIONS[item], index=index, key=key)


def date_period(
    prefix: str = "period",
    default_start: date | None = None,
    default_end: date | None = None,
    allow_empty: bool = False,
) -> tuple[date | None, date | None]:
    """Отображает два поля выбора дат периода.

    Args:
        prefix: Префикс ключей Streamlit-виджетов.
        default_start: Начальная дата по умолчанию.
        default_end: Конечная дата по умолчанию.
        allow_empty: Разрешает пустые значения дат без автоподстановки.

    Returns:
        Кортеж из начальной и конечной даты или None для пустых полей.
    """

    today = date.today()
    stored_start = None if allow_empty else st.session_state.get("dashboard_date_from")
    stored_end = None if allow_empty else st.session_state.get("dashboard_date_to")
    fallback_start = None if allow_empty else date(today.year - 5, 1, 1)
    fallback_end = None if allow_empty else today
    start = st.date_input("Начало периода", value=default_start or stored_start or fallback_start, key=f"{prefix}_date_from")
    end = st.date_input("Конец периода", value=default_end or stored_end or fallback_end, key=f"{prefix}_date_to")
    return start, end


def common_filters(prefix: str = "filters") -> dict[str, Any]:
    """Отображает общий набор фильтров анализа.

    Args:
        prefix: Префикс ключей Streamlit-виджетов.

    Returns:
        Словарь выбранных фильтров и загруженных справочников.

    Raises:
        ApiError: Если backend вернул ошибку загрузки справочников.
    """

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
    """Отображает выбор методов анализа временного ряда.

    Returns:
        Список кодов выбранных методов анализа.
    """

    options = list(ANALYSIS_METHOD_LABELS)
    return st.multiselect(
        "Методы анализа",
        options=options,
        default=options,
        format_func=lambda item: ANALYSIS_METHOD_LABELS.get(item, item),
    )


def analysis_options(prefix: str = "analysis") -> dict[str, Any]:
    """Отображает дополнительные параметры методов анализа.

    Args:
        prefix: Префикс ключей Streamlit-виджетов.

    Returns:
        Словарь options для `POST /analysis/run`.
    """

    window = st.number_input("Окно скользящего среднего", min_value=2, max_value=120, value=12, step=1, key=f"{prefix}_ma_window")
    extremes_count = st.number_input("Количество экстремумов в таблице", min_value=3, max_value=20, value=5, step=1, key=f"{prefix}_extremes_count")
    norm_start, norm_end = date_period(prefix=f"{prefix}_norm")
    return {
        "moving_average_window": int(window),
        "window": int(window),
        "extremes_count": int(extremes_count),
        "top_n": int(extremes_count),
        "seasonal_period": 12,
        "norm_period_start": norm_start.isoformat(),
        "norm_period_end": norm_end.isoformat(),
    }


def render_availability(station: Any, parameter: Any) -> None:
    """Отображает доступный период наблюдений для выбранной пары.

    Args:
        station: Идентификатор станции.
        parameter: Идентификатор параметра.

    Returns:
        None.
    """

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
    """Проверяет обязательные поля общего набора фильтров.

    Args:
        filters: Словарь фильтров страницы.

    Returns:
        Результат валидации обязательных полей.
    """

    return validate_required_filters(filters.get("station_id"), filters.get("parameter_id"), filters.get("date_from"), filters.get("date_to"))
