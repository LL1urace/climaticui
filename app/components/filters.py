"""Shared filters for working pages."""

from __future__ import annotations

from datetime import date
from typing import Any

import streamlit as st

from app.api import dictionaries, observations
from app.state.session import persisted_form_value, remember_form_value
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

CALENDAR_MIN_DATE = date.min
CALENDAR_MAX_DATE = date.max
CALENDAR_HELP = "Можно выбрать любую дату. Если за период нет наблюдений, приложение покажет предупреждение."


def _remember_shared_widget_value(widget_key: str, shared_key: str) -> None:
    """Сохраняет изменение основного поля до повторной отрисовки страницы."""

    value = st.session_state.get(widget_key)
    st.session_state[shared_key] = value
    if shared_key == "selected_station_id":
        st.session_state["dashboard_station_ids"] = [value] if value is not None else []
    elif shared_key == "dashboard_station_ids":
        st.session_state["selected_station_id"] = value[0] if value else None


def persistent_selectbox(
    label: str,
    options: list[Any],
    key: str,
    default: Any = None,
    shared_key: str | None = None,
    **kwargs: Any,
) -> Any:
    """Отображает selectbox с локальным или общим сохранением значения."""

    stored_value = st.session_state.get(shared_key, default) if shared_key else persisted_form_value(key, default)
    index = options.index(stored_value) if stored_value in options else None
    if shared_key:
        kwargs["on_change"] = _remember_shared_widget_value
        kwargs["args"] = (key, shared_key)
    value = st.selectbox(label, options=options, index=index, key=key, **kwargs)
    if shared_key:
        st.session_state[shared_key] = value
    else:
        remember_form_value(key, value)
    return value


def persistent_multiselect(
    label: str,
    options: list[Any],
    key: str,
    default: list[Any] | None = None,
    shared_key: str | None = None,
    **kwargs: Any,
) -> list[Any]:
    """Отображает multiselect с локальным или общим сохранением значения."""

    stored_value = st.session_state.get(shared_key, default or []) if shared_key else persisted_form_value(key, default or [])
    selected = [item for item in stored_value if item in options] if isinstance(stored_value, list) else []
    widget_options = {"options": options, "key": key, **kwargs}
    if shared_key:
        widget_options["on_change"] = _remember_shared_widget_value
        widget_options["args"] = (key, shared_key)
    if key not in st.session_state:
        widget_options["default"] = selected
    value = st.multiselect(label, **widget_options)
    if shared_key:
        st.session_state[shared_key] = value
    else:
        remember_form_value(key, value)
    return value


def persistent_number_input(label: str, key: str, default: int | float, **kwargs: Any) -> int | float:
    """Отображает числовое поле и сохраняет значение между страницами."""

    value = st.number_input(label, value=persisted_form_value(key, default), key=key, **kwargs)
    remember_form_value(key, value)
    return value


def persistent_text_input(label: str, key: str, default: str = "", **kwargs: Any) -> str:
    """Отображает текстовое поле и сохраняет значение между страницами."""

    value = st.text_input(label, value=persisted_form_value(key, default), key=key, **kwargs)
    remember_form_value(key, value)
    return value


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
    previous = st.session_state.get("selected_station_id")
    selected = persistent_selectbox(
        "Метеостанция",
        options,
        key,
        default=previous,
        shared_key="selected_station_id",
        placeholder="Выберите метеостанцию",
        format_func=lambda item_id: station_label(by_id[item_id]),
    )
    if selected != previous:
        st.session_state["dashboard_station_ids"] = [selected] if selected is not None else []
    return selected


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
    selected = persistent_multiselect(
        "Метеостанции",
        options,
        key,
        default=[item_id for item_id in stored_default if item_id in options],
        shared_key="dashboard_station_ids",
        format_func=lambda item_id: station_label(by_id[item_id]),
    )
    st.session_state["dashboard_station_ids"] = selected
    st.session_state["selected_station_id"] = selected[0] if selected else None
    return selected


def select_parameter(
    parameters: list[dict],
    key: str = "parameter_select",
    label: str = "Параметр",
    inherit_context: bool = True,
    remember_context: bool = True,
) -> Any:
    """Отображает selectbox выбора климатического параметра.

    Args:
        parameters: Список параметров из backend API.
        key: Уникальный ключ Streamlit-виджета.
        label: Подпись поля выбора.
        inherit_context: Нужно ли использовать общий параметр как стартовое значение.
        remember_context: Нужно ли использовать параметр как общий контекст страниц.

    Returns:
        Идентификатор выбранного параметра или None.
    """

    if not parameters:
        st.warning("Backend не вернул список параметров.")
        return None
    options = [parameter_id(parameter) for parameter in parameters]
    by_id = {parameter_id(parameter): parameter for parameter in parameters}
    default = st.session_state.get("selected_parameter_id") if inherit_context else None
    selected = persistent_selectbox(
        label,
        options,
        key,
        default=default,
        shared_key="selected_parameter_id" if remember_context else None,
        placeholder="Выберите параметр",
        format_func=lambda item_id: parameter_label(by_id[item_id]),
    )
    return selected


def select_aggregation(key: str = "aggregation_select") -> str:
    """Отображает выбор типа агрегации временного ряда.

    Args:
        key: Уникальный ключ Streamlit-виджета.

    Returns:
        Код выбранной агрегации.
    """

    options = list(AGGREGATIONS)
    default = st.session_state.get("dashboard_aggregation")
    selected = persistent_selectbox(
        "Агрегация",
        options,
        key,
        default=default if default in options else "monthly",
        shared_key="dashboard_aggregation",
        format_func=lambda item: AGGREGATIONS[item],
    )
    st.session_state["dashboard_aggregation"] = selected
    return selected


def date_period(
    prefix: str = "period",
    default_start: date | None = None,
    default_end: date | None = None,
    inherit_dashboard: bool = True,
    remember_dashboard: bool = True,
) -> tuple[date | None, date | None]:
    """Отображает два поля выбора дат периода.

    Args:
        prefix: Префикс ключей Streamlit-виджетов.
        default_start: Начальная дата по умолчанию.
        default_end: Конечная дата по умолчанию.
        inherit_dashboard: Использовать ли общий период как стартовое значение.
        remember_dashboard: Обновлять ли общий период после изменения.

    Returns:
        Кортеж из начальной и конечной даты или None для пустых полей.
    """

    start_key = f"{prefix}_date_from"
    end_key = f"{prefix}_date_to"
    shared_start = st.session_state.get("dashboard_date_from") if inherit_dashboard else None
    shared_end = st.session_state.get("dashboard_date_to") if inherit_dashboard else None
    fallback_start = default_start or shared_start
    fallback_end = default_end or shared_end
    stored_start = st.session_state.get("dashboard_date_from", fallback_start) if remember_dashboard else persisted_form_value(start_key, fallback_start)
    stored_end = st.session_state.get("dashboard_date_to", fallback_end) if remember_dashboard else persisted_form_value(end_key, fallback_end)
    start = st.date_input(
        "Начало периода",
        value=stored_start,
        min_value=CALENDAR_MIN_DATE,
        max_value=CALENDAR_MAX_DATE,
        help=CALENDAR_HELP,
        key=start_key,
        on_change=_remember_shared_widget_value if remember_dashboard else None,
        args=(start_key, "dashboard_date_from") if remember_dashboard else None,
    )
    end = st.date_input(
        "Конец периода",
        value=stored_end,
        min_value=CALENDAR_MIN_DATE,
        max_value=CALENDAR_MAX_DATE,
        help=CALENDAR_HELP,
        key=end_key,
        on_change=_remember_shared_widget_value if remember_dashboard else None,
        args=(end_key, "dashboard_date_to") if remember_dashboard else None,
    )
    if remember_dashboard:
        st.session_state["dashboard_date_from"] = start
        st.session_state["dashboard_date_to"] = end
    else:
        remember_form_value(start_key, start)
        remember_form_value(end_key, end)
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
    render_period_availability_notice([station], [parameter], date_from, date_to)
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
    return persistent_multiselect(
        "Методы анализа",
        options,
        key="analysis_methods",
        default=[],
        format_func=lambda item: ANALYSIS_METHOD_LABELS.get(item, item),
    )


def analysis_options(prefix: str = "analysis", station: Any = None, parameter: Any = None) -> dict[str, Any]:
    """Отображает дополнительные параметры методов анализа.

    Args:
        prefix: Префикс ключей Streamlit-виджетов.
        station: Идентификатор выбранной станции.
        parameter: Идентификатор выбранного климатического параметра.

    Returns:
        Словарь options для `POST /analysis/run`.
    """

    window = persistent_number_input(
        "Окно скользящего среднего",
        key=f"{prefix}_ma_window",
        default=12,
        min_value=2,
        max_value=120,
        step=1,
    )
    extremes_count = persistent_number_input(
        "Количество экстремумов в таблице",
        key=f"{prefix}_extremes_count",
        default=5,
        min_value=3,
        max_value=20,
        step=1,
    )
    norm_start, norm_end = date_period(
        prefix=f"{prefix}_norm",
        inherit_dashboard=False,
        remember_dashboard=False,
    )
    render_period_availability_notice(
        [station],
        [parameter],
        norm_start,
        norm_end,
        label="Период климатической нормы",
    )
    options = {
        "moving_average_window": int(window),
        "window": int(window),
        "extremes_count": int(extremes_count),
        "top_n": int(extremes_count),
        "seasonal_period": 12,
    }
    if norm_start and norm_end:
        options["norm_period_start"] = norm_start.isoformat()
        options["norm_period_end"] = norm_end.isoformat()
    return options


def _parse_availability_date(value: Any) -> date | None:
    """Преобразует дату доступности из backend API в объект даты.

    Args:
        value: Значение даты в формате ISO или объект даты.

    Returns:
        Дата или None, если значение невозможно преобразовать.
    """

    if isinstance(value, date):
        return value
    if isinstance(value, str):
        try:
            return date.fromisoformat(value[:10])
        except ValueError:
            return None
    return None


def availability_period_message(
    date_from: date | None,
    date_to: date | None,
    available_from: Any,
    available_to: Any,
) -> tuple[str, str] | None:
    """Формирует уведомление о пересечении периода с доступными наблюдениями.

    Args:
        date_from: Начало выбранного пользователем периода.
        date_to: Конец выбранного пользователем периода.
        available_from: Начало доступного периода из backend API.
        available_to: Конец доступного периода из backend API.

    Returns:
        Кортеж из типа уведомления и текста или None, если уведомление не нужно.
    """

    availability_start = _parse_availability_date(available_from)
    availability_end = _parse_availability_date(available_to)
    if not date_from or not date_to or not availability_start or not availability_end:
        return None
    available_period = f"{availability_start.isoformat()} - {availability_end.isoformat()}"
    if date_to < availability_start or date_from > availability_end:
        return "warning", f"За выбранный период наблюдений нет. Доступные данные: {available_period}."
    if date_from < availability_start or date_to > availability_end:
        return "info", f"Часть выбранного периода не содержит наблюдений. Доступные данные: {available_period}."
    return None


def availability_ranges_message(
    date_from: date | None,
    date_to: date | None,
    ranges: list[tuple[Any, Any]],
) -> tuple[str, str] | None:
    """Формирует уведомление по нескольким диапазонам доступности.

    Args:
        date_from: Начало выбранного пользователем периода.
        date_to: Конец выбранного пользователем периода.
        ranges: Диапазоны доступности станций и параметров.

    Returns:
        Кортеж из типа уведомления и текста или None, если уведомление не нужно.
    """

    if not date_from or not date_to:
        return None
    parsed_ranges = [
        (range_start, range_end)
        for available_from, available_to in ranges
        if (range_start := _parse_availability_date(available_from))
        and (range_end := _parse_availability_date(available_to))
    ]
    if not parsed_ranges:
        return None
    earliest = min(range_start for range_start, _ in parsed_ranges)
    latest = max(range_end for _, range_end in parsed_ranges)
    available_period = f"{earliest.isoformat()} - {latest.isoformat()}"
    overlapping_ranges = [
        (range_start, range_end)
        for range_start, range_end in parsed_ranges
        if date_from <= range_end and date_to >= range_start
    ]
    if not overlapping_ranges:
        return "warning", f"За выбранный период наблюдений нет. Доступные данные: {available_period}."
    if len(overlapping_ranges) < len(parsed_ranges) or date_from < earliest or date_to > latest:
        return "info", f"Часть выбранного периода не содержит наблюдений. Доступные данные: {available_period}."
    return None


def _availability_issue(
    date_from: date | None,
    date_to: date | None,
    available_from: Any,
    available_to: Any,
) -> tuple[str, str] | None:
    """Определяет проблему покрытия выбранного периода наблюдениями.

    Args:
        date_from: Начало выбранного периода.
        date_to: Конец выбранного периода.
        available_from: Начало доступного диапазона.
        available_to: Конец доступного диапазона.

    Returns:
        Тип проблемы и доступный диапазон или None, если период покрыт полностью.
    """

    availability_start = _parse_availability_date(available_from)
    availability_end = _parse_availability_date(available_to)
    if not date_from or not date_to or not availability_start or not availability_end:
        return None
    available_period = f"{availability_start.isoformat()} - {availability_end.isoformat()}"
    if date_to < availability_start or date_from > availability_end:
        return "missing", available_period
    if date_from < availability_start or date_to > availability_end:
        return "partial", available_period
    return None


def availability_details_message(
    date_from: date | None,
    date_to: date | None,
    entries: list[dict[str, Any]],
) -> tuple[str, str] | None:
    """Формирует подробное уведомление о проблемных станциях и параметрах.

    Args:
        date_from: Начало выбранного периода.
        date_to: Конец выбранного периода.
        entries: Источники данных с подписями и диапазонами доступности.

    Returns:
        Тип и текст уведомления или None, если все диапазоны покрывают период.
    """

    if not date_from or not date_to:
        return None
    grouped_issues: dict[tuple[str, str, str], set[str]] = {}
    for entry in entries:
        issue = _availability_issue(date_from, date_to, entry.get("date_from"), entry.get("date_to"))
        if not issue:
            continue
        issue_type, available_period = issue
        key = (str(entry.get("station") or "Метеостанция"), issue_type, available_period)
        parameter = entry.get("parameter")
        if parameter:
            grouped_issues.setdefault(key, set()).add(str(parameter))
        else:
            grouped_issues.setdefault(key, set())

    if not grouped_issues:
        return None

    has_missing = any(issue_type == "missing" for _, issue_type, _ in grouped_issues)
    message_type = "warning" if has_missing else "info"
    selected_period = f"{date_from.isoformat()} - {date_to.isoformat()}"
    lines = []
    for (station, issue_type, available_period), parameters in sorted(grouped_issues.items()):
        issue_text = "наблюдений нет" if issue_type == "missing" else "период покрыт частично"
        parameters_text = f" · параметры: {', '.join(sorted(parameters))}" if parameters else ""
        lines.append(f"- **{station}**{parameters_text}: {issue_text}; доступно: `{available_period}`.")
    summary = "Есть проблемы с доступностью наблюдений:"
    return message_type, f"Выбранный период: `{selected_period}`.\n\n{summary}\n" + "\n".join(lines)


def _station_notice_label(station: Any) -> str:
    """Возвращает подпись станции для уведомления о доступности.

    Args:
        station: Идентификатор или запись метеостанции.

    Returns:
        Человекочитаемая подпись станции.
    """

    if isinstance(station, dict):
        return station_label(station)
    stations = st.session_state.get("cached_stations") or []
    for record in stations:
        if str(station_id(record)) == str(station):
            return station_label(record)
    return f"Станция {station}"


def _parameter_notice_label(parameter: Any) -> str:
    """Возвращает подпись параметра для уведомления о доступности.

    Args:
        parameter: Идентификатор или запись климатического параметра.

    Returns:
        Человекочитаемая подпись параметра.
    """

    if isinstance(parameter, dict):
        return parameter_label(parameter)
    parameters = st.session_state.get("cached_parameters") or []
    for record in parameters:
        if str(parameter_id(record)) == str(parameter):
            return parameter_label(record)
    return f"Параметр {parameter}"


def _cached_availability(station: Any, parameter: Any) -> dict | None:
    """Получает доступность наблюдений через API и сохраняет её в session state.

    Args:
        station: Идентификатор станции.
        parameter: Идентификатор климатического параметра.

    Returns:
        Словарь доступности или None, если API не вернул данные.
    """

    if station is None or parameter is None:
        return None
    cache = st.session_state.setdefault("cached_observation_availability", {})
    cache_key = f"{station}:{parameter}"
    if cache_key not in cache:
        try:
            availability = observations.get_availability(station, parameter)
        except Exception:
            availability = None
        cache[cache_key] = availability if isinstance(availability, dict) else None
    return cache[cache_key]


def _render_period_message(message: tuple[str, str] | None, label: str | None = None) -> None:
    """Отображает сообщение о доступности выбранного периода.

    Args:
        message: Тип и текст уведомления или None.
        label: Необязательная подпись проверяемого периода.

    Returns:
        None.
    """

    if not message:
        return
    message_type, text = message
    text = f"**{label}**\n\n{text}" if label else text
    if message_type == "warning":
        st.warning(text)
    else:
        st.info(text)


def render_period_availability_notice(
    station_ids: list[Any],
    parameter_ids: list[Any],
    date_from: date | None,
    date_to: date | None,
    label: str | None = None,
) -> None:
    """Проверяет через API и отображает доступность выбранного периода.

    Args:
        station_ids: Идентификаторы выбранных станций.
        parameter_ids: Идентификаторы выбранных климатических параметров.
        date_from: Начало выбранного периода.
        date_to: Конец выбранного периода.
        label: Необязательная подпись периода для уведомления.

    Returns:
        None.
    """

    entries = []
    for station in station_ids:
        for parameter in parameter_ids:
            availability = _cached_availability(station, parameter)
            if not availability:
                continue
            entries.append(
                {
                    "station": _station_notice_label(station),
                    "parameter": _parameter_notice_label(parameter),
                    "date_from": availability.get("date_min") or availability.get("date_from"),
                    "date_to": availability.get("date_max") or availability.get("date_to"),
                }
            )
    _render_period_message(availability_details_message(date_from, date_to, entries), label)


def render_station_period_availability_notice(
    stations: list[dict],
    date_from: date | None,
    date_to: date | None,
    parameter_ids: list[Any] | None = None,
) -> None:
    """Отображает доступность периода панели по API или метаданным станций.

    Args:
        stations: Выбранные станции с метаданными доступности.
        date_from: Начало выбранного периода.
        date_to: Конец выбранного периода.
        parameter_ids: Климатические параметры для проверки через API.

    Returns:
        None.
    """

    entries = []
    for station in stations:
        station_entries = []
        for parameter in parameter_ids or []:
            availability = _cached_availability(station_id(station), parameter)
            if not availability:
                continue
            station_entries.append(
                {
                    "station": _station_notice_label(station),
                    "parameter": _parameter_notice_label(parameter),
                    "date_from": availability.get("date_min") or availability.get("date_from"),
                    "date_to": availability.get("date_max") or availability.get("date_to"),
                }
            )
        if not station_entries:
            station_entries = [
                {
                    "station": _station_notice_label(station),
                    "parameter": "Температура",
                    "date_from": station.get("temp_start"),
                    "date_to": station.get("temp_end"),
                },
                {
                    "station": _station_notice_label(station),
                    "parameter": "Осадки",
                    "date_from": station.get("prcp_start"),
                    "date_to": station.get("prcp_end"),
                },
            ]
        entries.extend(station_entries)
    _render_period_message(availability_details_message(date_from, date_to, entries))


def render_availability(
    station: Any,
    parameter: Any,
    date_from: date | None = None,
    date_to: date | None = None,
) -> None:
    """Отображает доступный период наблюдений для выбранной пары.

    Args:
        station: Идентификатор станции.
        parameter: Идентификатор параметра.
        date_from: Начало выбранного пользователем периода.
        date_to: Конец выбранного пользователем периода.

    Returns:
        None.
    """

    if not station or not parameter:
        return
    availability = _cached_availability(station, parameter)
    if not availability:
        return
    date_min = availability.get("date_min") or availability.get("date_from")
    date_max = availability.get("date_max") or availability.get("date_to")
    count = availability.get("count")
    if date_min or date_max or count:
        st.caption(f"Доступность: {date_min or '?'} - {date_max or '?'}; наблюдений: {count or '?'}")
    _render_period_message(availability_period_message(date_from, date_to, date_min, date_max))


def validate_common_filters(filters: dict[str, Any]) -> ValidationResult:
    """Проверяет обязательные поля общего набора фильтров.

    Args:
        filters: Словарь фильтров страницы.

    Returns:
        Результат валидации обязательных полей.
    """

    return validate_required_filters(filters.get("station_id"), filters.get("parameter_id"), filters.get("date_from"), filters.get("date_to"))
