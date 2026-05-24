from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

import streamlit as st

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.api.client import ApiError
from app.components.errors import render_api_error
from app.components.filters import date_period, load_stations, multiselect_stations, select_aggregation
from app.components.layout import page_title, setup_page
from app.components.maps import render_stations_map
from app.components.sidebar import render_sidebar
from app.state.session import init_session_state, remember_selection, require_auth
from app.utils.formatters import station_id, station_label


FEATURES = [
    {
        "title": "Анализ временного ряда",
        "text": "Базовая статистика, тренд, скользящее среднее, аномалии и климатическая норма.",
        "path": "pages/01_Analysis.py",
        "icon": "📈",
        "tone": "klima-card-blue",
    },
    {
        "title": "Сравнение периодов",
        "text": "Оцените, как изменилась выбранная метрика между двумя временными интервалами.",
        "path": "pages/02_Period_Comparison.py",
        "icon": "🧭",
        "tone": "klima-card-ink",
    },
    {
        "title": "Сравнение станций",
        "text": "Сопоставьте несколько метеостанций и посмотрите результат на карте.",
        "path": "pages/03_Station_Comparison.py",
        "icon": "📍",
        "tone": "klima-card-blue",
    },
    {
        "title": "Корреляционный анализ",
        "text": "Оцените связь между несколькими климатическими параметрами одной станции.",
        "path": "pages/08_Correlation.py",
        "icon": "🔗",
        "tone": "klima-card-ink",
    },
    {
        "title": "Климатограмма",
        "text": "Постройте месячный профиль температуры и осадков для выбранной станции.",
        "path": "pages/04_Climatogram.py",
        "icon": "🌦️",
        "tone": "klima-card-blue",
    },
    {
        "title": "Прогнозирование",
        "text": "Запустите исследовательский backend-прогноз с явным demo-warning.",
        "path": "pages/05_Forecasting.py",
        "icon": "🔮",
        "tone": "klima-card-blue",
    },
    {
        "title": "История и отчёты",
        "text": "Откройте прошлые запуски анализа и сформируйте скачиваемый отчёт.",
        "path": "pages/06_Analysis_History.py",
        "icon": "🗂️",
        "button_label": "История",
        "secondary_path": "pages/07_Reports.py",
        "secondary_icon": "📄",
        "secondary_label": "Отчёты",
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


def _map_selection_key(selected_station_ids: list[Any]) -> str:
    """Формирует ключ карты, зависящий от текущего выбора станций.

    Args:
        selected_station_ids: Текущий список выбранных метеостанций.

    Returns:
        Уникальный ключ виджета карты для текущего состояния выбора.
    """

    suffix = "_".join(_id_key(item_id) for item_id in selected_station_ids) or "empty"
    return f"dashboard_stations_map_{suffix}"


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
    button_key = f"open_{feature['path'].replace('/', '_').replace('.', '_')}"
    if feature.get("secondary_path"):
        secondary_key = f"open_{feature['secondary_path'].replace('/', '_').replace('.', '_')}"
        action_left, action_right = st.columns(2)
        with action_left:
            if st.button(f"{feature['icon']} {button_label}", key=button_key, use_container_width=True):
                st.switch_page(feature["path"])
        with action_right:
            if st.button(f"{feature['secondary_icon']} {feature['secondary_label']}", key=secondary_key, use_container_width=True):
                st.switch_page(feature["secondary_path"])
        return
    if st.button(f"{feature['icon']} {button_label}", key=button_key, use_container_width=True):
        st.switch_page(feature["path"])


setup_page("Исследовательская панель")
init_session_state()
require_auth()
render_sidebar()
page_title("Исследовательская панель", "Единое место для выбора периода, метеостанций и сценария анализа.")
_render_top_navigation()
_apply_pending_map_selection()

try:
    stations = load_stations()
except ApiError as error:
    render_api_error(error)
    st.stop()

default_station_ids = st.session_state.get("dashboard_station_ids") or []

st.markdown(
    """
    <div class="klima-hero">
        <span class="klima-kicker">Research control room</span>
        <h1>Соберите климатический срез перед анализом</h1>
        <p>
            Исследовательская панель хранит общий контекст работы: выбранные станции, период и агрегацию.
            Эти значения становятся стартовыми настройками для аналитических страниц.
        </p>
    </div>
    """,
    unsafe_allow_html=True,
)

st.subheader("Глобальные фильтры")
filter_cols = st.columns([0.56, 0.44])
with filter_cols[0]:
    selected_station_ids = multiselect_stations(stations, key="dashboard_station_multiselect", default_ids=default_station_ids)
with filter_cols[1]:
    aggregation = select_aggregation("dashboard_aggregation_select")

date_from, date_to = date_period("dashboard_period", allow_empty=True)
selected_stations = _selected_station_records(stations, selected_station_ids)

_remember_dashboard_filters(selected_station_ids, date_from, date_to, aggregation)
_render_slice_summary(selected_stations, date_from, date_to, aggregation)

st.subheader("Карта метеостанций")
st.caption("Кликните по точке, чтобы выбрать метеостанцию. Тёмные точки - выбранные станции, синие - доступные станции справочника.")
map_selected_station_ids = render_stations_map(
    stations,
    selected_ids=selected_station_ids,
    selectable=True,
    selection_key=_map_selection_key(selected_station_ids),
    selection_mode="multi-object",
)
if st.session_state.pop("dashboard_ignore_next_map_selection", False):
    map_selected_station_ids = None
next_station_ids = _next_station_selection(selected_station_ids, map_selected_station_ids)
if next_station_ids is not None and [_id_key(item) for item in next_station_ids] != [_id_key(item) for item in selected_station_ids]:
    st.session_state["dashboard_map_pending_station_ids"] = next_station_ids
    st.rerun()
_render_station_info_block(selected_stations)

st.subheader("Возможности анализа")
st.caption("Ниже находятся основные рабочие сценарии. Они используют выбранный выше контекст как стартовые значения.")

feature_rows = [FEATURES[index : index + 3] for index in range(0, len(FEATURES), 3)]
for row in feature_rows:
    cols = st.columns(3)
    for column, feature in zip(cols, row):
        with column:
            _render_feature_card(feature)
