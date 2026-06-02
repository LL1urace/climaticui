from __future__ import annotations

from html import escape
import math
import sys
from pathlib import Path
from typing import Any

import streamlit as st

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.api import comparisons, saved_sets
from app.api.client import ApiError
from app.components.errors import render_api_error
from app.components.filters import (
    date_period,
    load_parameters,
    load_stations,
    multiselect_stations,
    render_station_period_availability_notice,
    select_aggregation,
)
from app.components.layout import page_title, setup_page
from app.components.maps import (
    BASEMAP_LABELS,
    CLASSIFICATION_GRADIENT_LABELS,
    EURASIA_MAP_VIEW,
    classification_gradient_css,
    render_stations_map,
    station_map_palette,
)
from app.components.sidebar import render_sidebar
from app.state.session import clear_dashboard_context, init_session_state, remember_selection, require_auth
from app.utils.formatters import parameter_id, parameter_label, station_id, station_label, unwrap_records


FEATURES = [
    {
        "title": "Анализ временного ряда",
        "text": "Базовая статистика, тренд, скользящее среднее, аномалии и климатическая норма.",
        "path": "pages/01_Analysis.py",
        "icon": "📈",
        "button_label": "Открыть",
        "button_key": "open-analysis",
        "tone": "klima-card-blue",
    },
    {
        "title": "Сравнение периодов",
        "text": "Оцените, как изменилась выбранная метрика между двумя временными интервалами.",
        "path": "pages/02_Period_Comparison.py",
        "icon": "🧭",
        "button_label": "Открыть",
        "button_key": "open-period-comparison",
        "tone": "klima-card-ink",
    },
    {
        "title": "Сравнение станций",
        "text": "Сопоставьте несколько метеостанций и посмотрите результат на карте.",
        "path": "pages/03_Station_Comparison.py",
        "icon": "📍",
        "button_label": "Открыть",
        "button_key": "open-station-comparison",
        "tone": "klima-card-blue",
    },
    {
        "title": "Корреляционный анализ",
        "text": "Оцените связь между несколькими климатическими параметрами одной станции.",
        "path": "pages/08_Correlation.py",
        "icon": "🔗",
        "button_label": "Открыть",
        "button_key": "open-correlation",
        "tone": "klima-card-ink",
    },
    {
        "title": "Климатограмма",
        "text": "Постройте месячный профиль температуры и осадков для выбранной станции.",
        "path": "pages/04_Climatogram.py",
        "icon": "🌦️",
        "button_label": "Открыть",
        "button_key": "open-climatogram",
        "tone": "klima-card-blue",
    },
    {
        "title": "Прогнозирование",
        "text": "Запустите исследовательский backend-прогноз с явным demo-warning.",
        "path": "pages/05_Forecasting.py",
        "icon": "🔮",
        "button_label": "Открыть",
        "button_key": "open-forecasting",
        "tone": "klima-card-ink",
    },
    {
        "title": "История анализа",
        "text": "Откройте прошлые запуски анализа и вернитесь к сохранённым результатам.",
        "path": "pages/06_Analysis_History.py",
        "icon": "🗂️",
        "button_label": "Открыть историю",
        "button_key": "open-analysis-history",
        "tone": "klima-card-blue",
    },
    {
        "title": "Отчёты",
        "text": "Сформируйте скачиваемый отчёт по выбранным станциям, периоду и параметрам.",
        "path": "pages/07_Reports.py",
        "icon": "📄",
        "button_label": "Открыть отчёты",
        "button_key": "open-reports",
        "tone": "klima-card-ink",
    },
]

TOP_NAVIGATION = [
    {"label": "Анализ", "path": "pages/01_Analysis.py", "key": "analysis"},
    {"label": "Периоды", "path": "pages/02_Period_Comparison.py", "key": "periods"},
    {"label": "Станции", "path": "pages/03_Station_Comparison.py", "key": "stations"},
    {"label": "Корреляция", "path": "pages/08_Correlation.py", "key": "correlation"},
    {"label": "Климатограмма", "path": "pages/04_Climatogram.py", "key": "climatogram"},
    {"label": "Прогноз", "path": "pages/05_Forecasting.py", "key": "forecast"},
    {"label": "История", "path": "pages/06_Analysis_History.py", "key": "history"},
    {"label": "Отчёты", "path": "pages/07_Reports.py", "key": "reports"},
]

SAVE_SET_MODES = {
    "dashboard": "Дашборд",
    "analysis": "Анализ",
    "forecast": "Прогнозирование",
    "report": "Отчёт",
}
MAP_CLASSIFICATION_VALUE_KEY = "_classification_mean"


def _apply_pending_map_selection() -> None:
    """Применяет выбор станций с карты до отрисовки multiselect.

    Returns:
        None.
    """

    pending_ids = st.session_state.pop("dashboard_map_pending_station_ids", None)
    if pending_ids is None:
        return
    st.session_state["dashboard_station_ids"] = pending_ids
    st.session_state["dashboard_station_multiselect"] = pending_ids
    st.session_state["dashboard_ignore_next_map_selection"] = True


def _apply_pending_dashboard_reset() -> None:
    """Применяет подтверждённый сброс до создания виджетов фильтров.

    Returns:
        None.
    """

    if not st.session_state.pop("dashboard_reset_pending", False):
        return
    clear_dashboard_context()
    st.session_state["dashboard_station_multiselect"] = []
    st.session_state["dashboard_aggregation_select"] = "monthly"
    st.session_state["dashboard_period_date_from"] = None
    st.session_state["dashboard_period_date_to"] = None
    st.session_state["dashboard_reset_notice"] = True


@st.dialog("Сбросить данные панели?")
def _render_reset_dashboard_dialog() -> None:
    """Запрашивает подтверждение перед очисткой текущего аналитического среза.

    Returns:
        None.
    """

    st.warning(
        "Текущий выбор метеостанций, периода и агрегации будет сброшен. "
        "Если этот набор данных важен, сначала сохраните его в блоке «Сохранение набора анализа»."
    )
    st.caption(
        "Авторизация, справочники, сохранённые на backend наборы и визуальные настройки карты останутся без изменений."
    )
    cancel_column, confirm_column = st.columns(2)
    with cancel_column:
        if st.button("Отмена", key="cancel-dashboard-reset", use_container_width=True):
            st.rerun(scope="app")
    with confirm_column:
        if st.button("Да, сбросить", key="confirm-dashboard-reset", type="primary", use_container_width=True):
            st.session_state["dashboard_reset_pending"] = True
            st.rerun(scope="app")


def _render_top_navigation() -> None:
    """Отображает верхнюю навигацию к главной странице и инструментам анализа.

    Returns:
        None.
    """

    first_row_items = TOP_NAVIGATION[:4]
    second_row_items = TOP_NAVIGATION[4:]
    nav_selectors = ",\n".join(f".st-key-top-nav-{item['key']} button" for item in TOP_NAVIGATION)
    nav_text_selectors = ",\n".join(f".st-key-top-nav-{item['key']} button *" for item in TOP_NAVIGATION)
    nav_hover_selectors = ",\n".join(f".st-key-top-nav-{item['key']} button:hover" for item in TOP_NAVIGATION)
    st.markdown(
        f"""
        <style>
        {nav_selectors} {{
            background: linear-gradient(135deg, #17b6d6 0%, #0d64d8 48%, #07111f 100%) !important;
            border: 1px solid rgba(255, 255, 255, .32) !important;
            box-shadow: 0 14px 34px rgba(13, 100, 216, .20) !important;
            color: #f8fbff !important;
            min-height: 3.05rem !important;
            padding: .55rem .65rem !important;
            white-space: normal !important;
        }}

        {nav_text_selectors} {{
            color: #f8fbff !important;
            font-weight: 800 !important;
            font-size: .92rem !important;
            line-height: 1.15 !important;
            text-align: center !important;
            white-space: normal !important;
        }}

        {nav_hover_selectors} {{
            transform: translateY(-1px);
            box-shadow: 0 18px 44px rgba(7, 17, 31, .24) !important;
        }}

        .st-key-top_nav_home button {{
            min-height: 3.05rem !important;
            padding: .55rem .65rem !important;
            border: 1px solid rgba(255, 255, 255, .58) !important;
            background: linear-gradient(135deg, #9ff4df 0%, #76e4c5 52%, #17b6d6 100%) !important;
            box-shadow:
                0 14px 34px rgba(23, 182, 214, .20),
                0 0 0 3px rgba(118, 228, 197, .13) !important;
            color: #07111f !important;
            transition: transform .16s ease, box-shadow .16s ease, filter .16s ease !important;
        }}

        .st-key-top_nav_home button * {{
            color: #07111f !important;
            font-weight: 800 !important;
            font-size: .92rem !important;
        }}

        .st-key-top_nav_home button:hover {{
            box-shadow:
                0 18px 42px rgba(23, 182, 214, .30),
                0 0 0 4px rgba(118, 228, 197, .19) !important;
            filter: brightness(1.04);
            transform: translateY(-1px);
        }}

        @media (max-width: 900px) {{
            {nav_selectors} {{
                min-height: 3.35rem !important;
                padding: .5rem .45rem !important;
            }}

            {nav_text_selectors} {{
                font-size: .84rem !important;
            }}
        }}
        </style>
        """,
        unsafe_allow_html=True,
    )
    first_row = st.columns(5, gap="small")
    with first_row[0]:
        if st.button("На главную", key="top_nav_home", use_container_width=True):
            st.switch_page("main.py")

    for column, item in zip(first_row[1:], first_row_items):
        with column:
            if st.button(item["label"], key=f"top-nav-{item['key']}", use_container_width=True):
                st.switch_page(item["path"])

    second_row = st.columns(4, gap="small")
    for column, item in zip(second_row, second_row_items):
        with column:
            if st.button(item["label"], key=f"top-nav-{item['key']}", use_container_width=True):
                st.switch_page(item["path"])


def _selected_station_records(stations: list[dict], selected_ids: list[Any]) -> list[dict]:
    """Возвращает записи выбранных метеостанций.

    Args:
        stations: Список станций из backend API.
        selected_ids: Идентификаторы выбранных станций.

    Returns:
        Список записей станций, выбранных пользователем.
    """

    selected = set(selected_ids)
    return [station for station in stations if station_id(station) in selected]


def _id_key(value: Any) -> str:
    """Преобразует идентификатор станции в строковый ключ сравнения.

    Args:
        value: Идентификатор станции из фильтра или события карты.

    Returns:
        Строковый ключ идентификатора.
    """

    return str(value)


def _map_selection_key(
    selected_station_ids: list[Any],
    show_only_selected: bool = False,
    classification_parameter: Any = None,
    classification_gradient: str | None = None,
) -> str:
    """Формирует ключ карты, зависящий от текущего выбора станций.

    Args:
        selected_station_ids: Текущий список выбранных метеостанций.
        show_only_selected: Скрыты ли невыбранные станции.
        classification_parameter: Параметр тематической раскраски или None.
        classification_gradient: Палитра тематической раскраски или None.

    Returns:
        Уникальный ключ виджета карты для текущего состояния выбора.
    """

    suffix = "_".join(_id_key(item_id) for item_id in selected_station_ids) or "empty"
    mode = "selected_only" if show_only_selected else "all"
    classification = (
        f"classified_{classification_parameter}_{classification_gradient}"
        if classification_parameter is not None
        else "default"
    )
    return f"dashboard_stations_map_{mode}_{classification}_{suffix}"


def _next_station_selection(current_ids: list[Any], map_ids: list[Any] | None) -> list[Any] | None:
    """Рассчитывает следующий выбор станций после клика на карте.

    Args:
        current_ids: Текущие идентификаторы выбранных станций.
        map_ids: Идентификаторы станций, пришедшие из события карты.

    Returns:
        Новый список выбранных станций или None, если событие карты пустое.
    """

    if not map_ids:
        return None

    next_ids = list(current_ids)
    current_keys = {_id_key(item_id) for item_id in current_ids}

    if len(map_ids) == 1:
        clicked_id = map_ids[0]
        clicked_key = _id_key(clicked_id)
        if clicked_key in current_keys:
            return [item_id for item_id in next_ids if _id_key(item_id) != clicked_key]
        return next_ids + [clicked_id]

    seen_keys = set(current_keys)
    for item_id in map_ids:
        item_key = _id_key(item_id)
        if item_key in seen_keys:
            continue
        next_ids.append(item_id)
        seen_keys.add(item_key)
    return next_ids


def _remember_dashboard_filters(selected_station_ids: list[Any], date_from: Any, date_to: Any, aggregation: str) -> None:
    """Сохраняет глобальные фильтры исследовательской панели в session state.

    Args:
        selected_station_ids: Идентификаторы выбранных станций.
        date_from: Начальная дата общего периода.
        date_to: Конечная дата общего периода.
        aggregation: Код выбранной агрегации.

    Returns:
        None.
    """

    st.session_state["dashboard_station_ids"] = selected_station_ids
    st.session_state["dashboard_date_from"] = date_from
    st.session_state["dashboard_date_to"] = date_to
    st.session_state["dashboard_aggregation"] = aggregation
    remember_selection(station_id=selected_station_ids[0] if selected_station_ids else None)
    if not selected_station_ids:
        st.session_state["selected_station_id"] = None


def _map_classification_signature(
    stations: list[dict],
    classification_parameter: Any,
    date_from: Any,
    date_to: Any,
    aggregation: str,
) -> tuple[str, ...]:
    """Формирует ключ кэша тематической раскраски карты.

    Args:
        stations: Справочник отображаемых метеостанций.
        classification_parameter: Климатический параметр классификации.
        date_from: Начальная дата периода.
        date_to: Конечная дата периода.
        aggregation: Агрегация временных рядов.

    Returns:
        Hashable-подпись параметров расчёта средних значений.
    """

    station_ids = [station_id(station) for station in stations if station_id(station) is not None]
    return (
        str(classification_parameter),
        date_from.isoformat(),
        date_to.isoformat(),
        aggregation,
        str(len(station_ids)),
        str(station_ids[0]) if station_ids else "",
        str(station_ids[-1]) if station_ids else "",
    )


def _map_classification_values(
    stations: list[dict],
    classification_parameter: Any,
    date_from: Any,
    date_to: Any,
    aggregation: str,
) -> dict[str, float]:
    """Загружает средние значения параметра по станциям с session-кэшированием.

    Args:
        stations: Справочник отображаемых метеостанций.
        classification_parameter: Климатический параметр классификации.
        date_from: Начальная дата периода.
        date_to: Конечная дата периода.
        aggregation: Агрегация временных рядов.

    Returns:
        Словарь `station_id -> среднее значение`.

    Raises:
        ApiError: Если backend не смог рассчитать сравнение станций.
    """

    signature = _map_classification_signature(stations, classification_parameter, date_from, date_to, aggregation)
    cached = st.session_state.get("dashboard_map_classification_cache") or {}
    if cached.get("signature") == signature:
        return cached.get("values") or {}

    station_ids = [station_id(station) for station in stations if station_id(station) is not None]
    response = comparisons.compare_stations(
        {
            "station_ids": station_ids,
            "parameter_id": classification_parameter,
            "date_from": date_from.isoformat(),
            "date_to": date_to.isoformat(),
            "aggregation": aggregation,
            "metric": "mean",
            "skip_missing": True,
        }
    )
    values: dict[str, float] = {}
    for record in unwrap_records(response, ("stations", "results", "data", "items")):
        current_station_id = station_id(record)
        raw_value = record.get("mean")
        if raw_value is None:
            raw_value = record.get("value")
        try:
            number = float(raw_value)
        except (TypeError, ValueError):
            continue
        if current_station_id is not None and math.isfinite(number):
            values[_id_key(current_station_id)] = round(number, 3)

    st.session_state["dashboard_map_classification_cache"] = {
        "signature": signature,
        "values": values,
    }
    return values


def _classified_station_records(stations: list[dict], values: dict[str, float]) -> list[dict]:
    """Добавляет станциям средние значения для тематической карты.

    Args:
        stations: Справочник метеостанций.
        values: Средние значения по строковому идентификатору станции.

    Returns:
        Копии записей станций с полем значения классификации.
    """

    return [
        {
            **station,
            MAP_CLASSIFICATION_VALUE_KEY: values.get(_id_key(station_id(station))),
        }
        for station in stations
    ]


def _render_map_classification_legend(
    parameter: dict,
    values: dict[str, float],
    stations_count: int,
    gradient_name: str,
) -> None:
    """Отображает легенду градиента тематической карты.

    Args:
        parameter: Запись климатического параметра.
        values: Средние значения по станциям.
        stations_count: Общее количество точек на карте.
        gradient_name: Код выбранной цветовой палитры.

    Returns:
        None.
    """

    if not values:
        return

    lower = min(values.values())
    upper = max(values.values())
    title = escape(parameter_label(parameter))
    gradient_css = classification_gradient_css(gradient_name)
    st.markdown(
        f"""
        <div style="margin:.35rem 0 .55rem;padding:.85rem 1rem;border-radius:16px;
                    border:1px solid rgba(13,100,216,.16);background:rgba(255,255,255,.82);">
            <strong>Среднее за выбранный период: {title}</strong>
            <div style="height:.72rem;margin:.55rem 0 .28rem;border-radius:999px;
                        background:linear-gradient(90deg,{gradient_css});"></div>
            <div style="display:flex;justify-content:space-between;color:#39536f;font-size:.82rem;">
                <span>{lower:.2f}</span><span>{upper:.2f}</span>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    st.caption(
        f"Классифицировано станций: {len(values)} из {stations_count}. "
        "Все станции с данными окрашены по градиенту; точки без данных отображаются нейтральным цветом."
    )


def _saved_set_payloads(
    selected_station_ids: list[Any],
    parameters: list[dict],
    date_from: Any,
    date_to: Any,
    mode: str,
) -> list[dict[str, Any]]:
    """Формирует payload сохранённых наборов анализа.

    Args:
        selected_station_ids: Выбранные метеостанции.
        parameters: Все климатические показатели из справочника.
        date_from: Начальная дата периода.
        date_to: Конечная дата периода.
        mode: Режим работы набора.

    Returns:
        Список payload по одной записи на каждую станцию.
    """

    selected_parameter_ids = [parameter_id(parameter) for parameter in parameters if parameter_id(parameter) is not None]
    parameter = selected_parameter_ids[0] if selected_parameter_ids else None
    return [
        {
            "station_id": current_station_id,
            "parameter_id": parameter,
            "selected_parameters": selected_parameter_ids,
            "period_start": date_from.isoformat(),
            "period_end": date_to.isoformat(),
            "mode": mode,
        }
        for current_station_id in selected_station_ids
    ]


def _render_saved_set_block(
    selected_station_ids: list[Any],
    parameters: list[dict],
    date_from: Any,
    date_to: Any,
) -> None:
    """Отображает форму сохранения текущего аналитического набора.

    Args:
        selected_station_ids: Выбранные метеостанции.
        parameters: Список климатических параметров.
        date_from: Начальная дата периода.
        date_to: Конечная дата периода.

    Returns:
        None.
    """

    st.subheader("Сохранение набора анализа")
    st.caption(
        "Будет создана отдельная запись для каждой выбранной станции. "
        "Все климатические показатели сохраняются автоматически в selected_parameters, "
        "а в parameter_id записывается первый показатель из справочника для совместимости с backend-моделью."
    )
    with st.container(border=True, key="dashboard_saved_set_parameters"):
        mode = st.selectbox(
            "Режим набора",
            options=list(SAVE_SET_MODES),
            format_func=lambda item: SAVE_SET_MODES[item],
            key="dashboard_saved_set_mode",
        )
        parameter_count = len([parameter for parameter in parameters if parameter_id(parameter) is not None])
        st.caption(f"В набор будет включено климатических показателей: {parameter_count}.")

        can_save = bool(selected_station_ids and parameter_count and date_from and date_to)
        if not can_save:
            st.info("Чтобы сохранить набор, выберите станции и период. Список климатических показателей берётся автоматически.")

        if st.button("Сохранить набор анализа", type="primary", use_container_width=True, disabled=not can_save):
            payloads = _saved_set_payloads(selected_station_ids, parameters, date_from, date_to, mode)
            saved_records = []
            errors = []
            for payload in payloads:
                try:
                    saved_records.append(saved_sets.create_saved_analysis_set(payload))
                except ApiError as error:
                    errors.append(f"Станция {payload['station_id']}: {error}")
            if saved_records:
                st.session_state["last_saved_analysis_sets"] = saved_records
                st.success(f"Сохранено наборов: {len(saved_records)}.")
            for error in errors:
                st.error(error)

        saved_records = st.session_state.get("last_saved_analysis_sets") or []
        if saved_records:
            with st.expander("Последние сохранённые наборы", expanded=False):
                rows = [
                    {
                        "ID": record.get("id"),
                        "Станция": record.get("station_id"),
                        "Параметр": record.get("parameter_id"),
                        "Показатели": ", ".join(str(item) for item in record.get("selected_parameters") or []),
                        "Период": f"{record.get('period_start')} - {record.get('period_end')}",
                        "Режим": record.get("mode"),
                        "Создан": record.get("created_at"),
                    }
                    for record in saved_records
                ]
                st.dataframe(rows, hide_index=True, use_container_width=True)


def _safe_float(value: Any) -> float | None:
    """Преобразует значение станции в float, если это возможно.

    Args:
        value: Значение координаты или высоты из backend API.

    Returns:
        Число с плавающей точкой или None.
    """

    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _period_length_days(date_from: Any, date_to: Any) -> int | None:
    """Возвращает длительность выбранного периода в днях.

    Args:
        date_from: Начальная дата периода.
        date_to: Конечная дата периода.

    Returns:
        Количество дней периода или None, если даты не выбраны.
    """

    if not date_from or not date_to:
        return None
    return (date_to - date_from).days + 1


def _render_slice_summary(
    selected_stations: list[dict],
    date_from: Any,
    date_to: Any,
    aggregation: str,
) -> None:
    """Отображает сводку и статистику выбранного аналитического среза.

    Args:
        selected_stations: Записи выбранных станций из backend API.
        date_from: Начальная дата выбранного периода.
        date_to: Конечная дата выбранного периода.
        aggregation: Код выбранной агрегации.

    Returns:
        None.
    """

    latitudes = [_safe_float(station.get("latitude")) for station in selected_stations]
    longitudes = [_safe_float(station.get("longitude")) for station in selected_stations]
    elevations = [_safe_float(station.get("elevation")) for station in selected_stations]
    latitudes = [value for value in latitudes if value is not None]
    longitudes = [value for value in longitudes if value is not None]
    elevations = [value for value in elevations if value is not None]
    countries = {station.get("country") for station in selected_stations if station.get("country")}
    regions = {station.get("region") for station in selected_stations if station.get("region")}
    period_days = _period_length_days(date_from, date_to)

    st.subheader("Текущий срез")
    selected_count = len(selected_stations)
    period_label = f"{date_from.isoformat()} - {date_to.isoformat()}" if date_from and date_to else "не выбран"
    st.markdown(
        f"""
        <div class="klima-card klima-card-ink">
            <h3>Контекст анализа</h3>
            <p><strong>{selected_count}</strong> станций выбрано</p>
            <p>Период: {period_label}</p>
            <p>Агрегация: {aggregation}</p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.subheader("Сводка по выбранным данным")
    metric_cols = st.columns(3)
    metric_cols[0].metric("Стран в выборке", len(countries) if selected_count else 0)
    metric_cols[1].metric("Регионов в выборке", len(regions) if selected_count else 0)
    metric_cols[2].metric("Длительность периода", f"{period_days} дней" if period_days else "не выбрана")

    geo_cols = st.columns(3)
    lat_span = max(latitudes) - min(latitudes) if len(latitudes) > 1 else 0 if latitudes else None
    lon_span = max(longitudes) - min(longitudes) if len(longitudes) > 1 else 0 if longitudes else None
    mean_elevation = sum(elevations) / len(elevations) if elevations else None
    geo_cols[0].metric("Широтный охват", f"{lat_span:.2f}°" if lat_span is not None else "n/a")
    geo_cols[1].metric("Долготный охват", f"{lon_span:.2f}°" if lon_span is not None else "n/a")
    geo_cols[2].metric("Средняя высота", f"{mean_elevation:.0f} м" if mean_elevation is not None else "n/a")

    if not selected_stations:
        st.info("Выберите станции, чтобы сводка по географии и высотам стала информативной.")


def _render_station_info_block(selected_stations: list[dict]) -> None:
    """Отображает один блок с информацией о выбранных метеостанциях.

    Args:
        selected_stations: Записи метеостанций, выбранных пользователем.

    Returns:
        None.
    """

    if not selected_stations:
        return

    title = "Информация о метеостанции" if len(selected_stations) == 1 else "Информация о выбранных метеостанциях"
    st.subheader(title)
    if len(selected_stations) == 1:
        station = selected_stations[0]
        with st.container(border=True):
            st.markdown(f"### {station.get('name') or 'Метеостанция'}")
            info_cols = st.columns(4)
            info_cols[0].metric("Код", station.get("code") or "n/a")
            info_cols[1].metric("Регион", station.get("region") or "n/a")
            info_cols[2].metric("Широта", station.get("latitude") or "n/a")
            info_cols[3].metric("Долгота", station.get("longitude") or "n/a")
            st.caption(
                f"Страна: {station.get('country') or 'n/a'}; "
                f"высота: {station.get('elevation') or 'n/a'} м; "
                f"активна: {'да' if station.get('is_active', True) else 'нет'}."
            )
        return

    rows = [
        {
            "Станция": station_label(station),
            "Код": station.get("code"),
            "Страна": station.get("country"),
            "Регион": station.get("region"),
            "Широта": station.get("latitude"),
            "Долгота": station.get("longitude"),
            "Высота, м": station.get("elevation"),
        }
        for station in selected_stations
    ]
    st.dataframe(rows, hide_index=True, use_container_width=True)


def _render_feature_card(feature: dict[str, str]) -> None:
    """Отображает карточку возможности анализа и ссылку на страницу.

    Args:
        feature: Описание возможности с названием, текстом, путём, иконкой и стилем.

    Returns:
        None.
    """

    tone = feature.get("tone", "")
    st.markdown(
        f"""
        <div class="klima-card klima-feature-card {tone}">
            <h3>{feature["title"]}</h3>
            <p>{feature["text"]}</p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    button_label = feature.get("button_label", "Открыть")
    button_key = feature.get("button_key") or f"open_{feature['path'].replace('/', '_').replace('.', '_')}"

    if st.button(f"{feature['icon']} {button_label}", key=button_key, use_container_width=True):
        st.switch_page(feature["path"])


setup_page("Исследовательская панель")
init_session_state()
require_auth()
_apply_pending_dashboard_reset()
render_sidebar()
page_title("Исследовательская панель", "Единое место для выбора периода, метеостанций и сценария анализа.")
_render_top_navigation()
_apply_pending_map_selection()

try:
    stations = load_stations()
    parameters = load_parameters()
except ApiError as error:
    render_api_error(error)
    st.stop()

default_station_ids = st.session_state.get("dashboard_station_ids") or []

if not default_station_ids:
    st.session_state["dashboard_map_show_only_selected"] = False
with st.sidebar:
    st.subheader("Настройки карты")
    show_only_selected_on_map = st.checkbox(
        "Показывать только выбранные метеостанции",
        disabled=not default_station_ids,
        key="dashboard_map_show_only_selected",
    )
    classification_parameter_options = [
        parameter_id(parameter)
        for parameter in parameters
        if parameter_id(parameter) is not None
    ]
    parameters_by_id = {
        parameter_id(parameter): parameter
        for parameter in parameters
        if parameter_id(parameter) is not None
    }
    map_classification_enabled = st.checkbox(
        "Классификация по среднему значению",
        key="dashboard_map_classification_enabled",
    )
    map_classification_parameter = st.selectbox(
        "Параметр классификации",
        options=classification_parameter_options,
        format_func=lambda item: parameter_label(parameters_by_id[item]),
        disabled=not map_classification_enabled,
        key="dashboard_map_classification_parameter",
    )
    map_classification_gradient = st.selectbox(
        "Цветовой градиент",
        options=list(CLASSIFICATION_GRADIENT_LABELS),
        format_func=lambda item: CLASSIFICATION_GRADIENT_LABELS[item],
        disabled=not map_classification_enabled,
        key="dashboard_map_classification_gradient",
    )
    selected_station_color = st.color_picker(
        "Выбранные станции",
        value="#f59e0b",
        key="dashboard_map_selected_color",
    )
    real_station_color = st.color_picker(
        "Станции с реальными данными",
        value="#4a95ff",
        key="dashboard_map_real_color",
    )
    synthetic_station_color = st.color_picker(
        "Станции со сгенерированными данными",
        value="#062245",
        key="dashboard_map_synthetic_color",
    )
    dashboard_map_basemap = st.selectbox(
        "Подложка карты",
        options=list(BASEMAP_LABELS),
        format_func=lambda item: BASEMAP_LABELS[item],
        key="dashboard_map_basemap",
    )
    st.caption(
        "Классификация использует средние значения за выбранный период. "
        "При её включении все станции окрашиваются по единому градиенту."
    )
dashboard_map_palette = station_map_palette(
    selected_station_color,
    real_station_color,
    synthetic_station_color,
)

st.markdown(
    """
    <div class="klima-hero">
        <span class="klima-kicker">Исследовательский центр</span>
        <h1>Соберите климатический срез перед анализом</h1>
        <p>
            Исследовательская панель хранит общий контекст работы: выбранные станции, период и агрегацию.
            Эти значения становятся стартовыми настройками для аналитических страниц.
        </p>
    </div>
    """,
    unsafe_allow_html=True,
)

st.markdown(
    """
    <style>
    .st-key-open-dashboard-reset button {
        background: rgba(255, 176, 32, .16) !important;
        border: 1px solid rgba(234, 88, 12, .46) !important;
        color: #9a3412 !important;
        min-height: 2.75rem !important;
        box-shadow: 0 10px 24px rgba(234, 88, 12, .12) !important;
    }
    .st-key-open-dashboard-reset button:hover {
        background: rgba(255, 176, 32, .26) !important;
        border-color: rgba(234, 88, 12, .72) !important;
        transform: translateY(-1px);
    }
    .st-key-open-dashboard-reset button * {
        color: #9a3412 !important;
        font-weight: 800 !important;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

with st.container(border=True, key="dashboard_global_filters"):
    filter_title_column, reset_column = st.columns([0.72, 0.28], vertical_alignment="bottom")
    with filter_title_column:
        st.subheader("Глобальные фильтры")
    with reset_column:
        if st.button("🧹 Быстрый сброс данных", key="open-dashboard-reset", use_container_width=True):
            _render_reset_dashboard_dialog()

    if st.session_state.pop("dashboard_reset_notice", False):
        st.success("Данные панели сброшены. Можно собрать новый аналитический срез.")

    filter_cols = st.columns([0.56, 0.44])
    with filter_cols[0]:
        selected_station_ids = multiselect_stations(stations, key="dashboard_station_multiselect", default_ids=default_station_ids)
    with filter_cols[1]:
        aggregation = select_aggregation("dashboard_aggregation_select")

    date_from, date_to = date_period("dashboard_period", allow_empty=True)
    selected_stations = _selected_station_records(stations, selected_station_ids)

    _remember_dashboard_filters(selected_station_ids, date_from, date_to, aggregation)
    render_station_period_availability_notice(
        selected_stations,
        date_from,
        date_to,
        [parameter_id(parameter) for parameter in parameters if parameter_id(parameter) is not None],
    )
    _render_slice_summary(selected_stations, date_from, date_to, aggregation)

st.subheader("Карта метеостанций")
st.caption(
    "Кликните по точке, чтобы выбрать метеостанцию. "
    "Настройки цветов и тематической классификации находятся в sidebar."
)

map_station_records = stations
map_value_key = None
map_value_label = None
map_classification = None
if map_classification_enabled:
    if date_from and date_to:
        try:
            with st.spinner("Рассчитываю средние значения для классификации карты..."):
                classification_values = _map_classification_values(
                    stations,
                    map_classification_parameter,
                    date_from,
                    date_to,
                    aggregation,
                )
        except ApiError as error:
            st.warning(f"Не удалось построить классификацию карты: {error}")
            classification_values = {}

        if classification_values:
            classification_parameter = parameters_by_id.get(map_classification_parameter, {})
            map_station_records = _classified_station_records(stations, classification_values)
            map_value_key = MAP_CLASSIFICATION_VALUE_KEY
            map_value_label = f"Среднее за период · {parameter_label(classification_parameter)}"
            map_classification = {
                "value_key": MAP_CLASSIFICATION_VALUE_KEY,
                "min_value": min(classification_values.values()),
                "max_value": max(classification_values.values()),
                "gradient_name": map_classification_gradient,
            }
            _render_map_classification_legend(
                classification_parameter,
                classification_values,
                len(stations),
                map_classification_gradient,
            )
        else:
            st.warning("Для выбранного параметра и периода нет значений для классификации карты.")
    else:
        st.info("Чтобы включить классификацию карты, выберите начало и конец периода в глобальных фильтрах.")

map_selected_station_ids = render_stations_map(
    map_station_records,
    value_key=map_value_key,
    value_label=map_value_label,
    selected_ids=selected_station_ids,
    selectable=True,
    selection_key=_map_selection_key(
        selected_station_ids,
        show_only_selected_on_map,
        map_classification_parameter if map_classification else None,
        map_classification_gradient if map_classification else None,
    ),
    selection_mode="multi-object",
    show_only_selected=show_only_selected_on_map,
    initial_view_state=EURASIA_MAP_VIEW,
    color_map=dashboard_map_palette,
    classification=map_classification,
    fit_visible_points=show_only_selected_on_map,
    basemap=dashboard_map_basemap,
)
if st.session_state.pop("dashboard_ignore_next_map_selection", False):
    map_selected_station_ids = None
next_station_ids = _next_station_selection(selected_station_ids, map_selected_station_ids)
if next_station_ids is not None and [_id_key(item) for item in next_station_ids] != [_id_key(item) for item in selected_station_ids]:
    st.session_state["dashboard_map_pending_station_ids"] = next_station_ids
    st.rerun()
_render_station_info_block(selected_stations)

feature_button_selectors = ",\n".join(
    f".st-key-{feature['button_key']} button"
    for feature in FEATURES
    if feature.get("button_key")
)

feature_button_text_selectors = ",\n".join(
    f".st-key-{feature['button_key']} button *"
    for feature in FEATURES
    if feature.get("button_key")
)

feature_button_hover_selectors = ",\n".join(
    f".st-key-{feature['button_key']} button:hover"
    for feature in FEATURES
    if feature.get("button_key")
)

st.markdown(
    f"""
    <style>
    {feature_button_selectors} {{
        min-height: 3.65rem !important;
        background: linear-gradient(135deg, #ffb020 0%, #f97316 55%, #ea580c 100%) !important;
        border: 1px solid rgba(255, 255, 255, .78) !important;
        box-shadow:
            0 16px 34px rgba(234, 88, 12, .34),
            0 0 0 4px rgba(249, 115, 22, .14) !important;
        color: #ffffff !important;
        font-size: 1.05rem !important;
        letter-spacing: .01em !important;
        transition: transform .16s ease, box-shadow .16s ease, filter .16s ease !important;
    }}

    {feature_button_text_selectors} {{
        color: #ffffff !important;
        font-weight: 800 !important;
    }}

    {feature_button_hover_selectors} {{
        transform: translateY(-1px);
        filter: brightness(1.04);
        box-shadow:
            0 20px 42px rgba(234, 88, 12, .42),
            0 0 0 5px rgba(249, 115, 22, .18) !important;
    }}
    </style>
    """,
    unsafe_allow_html=True,
)

st.subheader("Возможности анализа")
st.caption("Ниже находятся основные рабочие сценарии. Они используют выбранный выше контекст как стартовые значения.")

feature_rows = [FEATURES[index : index + 3] for index in range(0, len(FEATURES), 3)]
for row in feature_rows:
    cols = st.columns(3)
    for column, feature in zip(cols, row):
        with column:
            _render_feature_card(feature)

_render_saved_set_block(selected_station_ids, parameters, date_from, date_to)
