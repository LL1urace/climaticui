from __future__ import annotations

from typing import Any

import streamlit as st

from klimatika_frontend.api import analysis
from klimatika_frontend.api.client import ApiError
from klimatika_frontend.components.charts import render_multi_climatograms
from klimatika_frontend.components.errors import render_api_error
from klimatika_frontend.components.filters import date_period, load_parameters, load_stations, multiselect_stations, select_parameter
from klimatika_frontend.components.layout import page_title, render_home_button, setup_page
from klimatika_frontend.components.sidebar import render_sidebar
from klimatika_frontend.components.tables import render_json_preview, render_table
from klimatika_frontend.state.session import init_session_state, require_auth
from klimatika_frontend.utils.formatters import station_id, station_label, unwrap_records
from klimatika_frontend.utils.validators import validate_period


TEMPERATURE_COLORS = ["#dc2626", "#f97316", "#be123c", "#ef4444", "#a16207", "#7f1d1d"]
PRECIPITATION_COLORS = ["#0d64d8", "#17b6d6", "#0891b2", "#4f46e5", "#0369a1", "#7c3aed"]


def _station_lookup(stations: list[dict]) -> dict[Any, dict]:
    """Возвращает справочник станций по идентификатору.

    Args:
        stations: Список станций из backend API.

    Returns:
        Словарь station_id -> запись станции.
    """

    return {station_id(station): station for station in stations}


def _period_count() -> int:
    """Возвращает количество периодов для формы климатограммы.

    Returns:
        Количество периодов из session state.
    """

    if "climatogram_period_count" not in st.session_state:
        st.session_state["climatogram_period_count"] = 1
    return int(st.session_state["climatogram_period_count"])


def _clear_climatogram_results() -> None:
    """Очищает сохранённые результаты климатограмм.

    Returns:
        None.
    """

    st.session_state["last_climatogram_items"] = []
    st.session_state["last_climatogram_errors"] = []
    st.session_state["last_climatogram_signature"] = None


def _drop_period_state(index: int) -> None:
    """Удаляет состояние виджетов скрытого периода.

    Args:
        index: Индекс периода, который больше не отображается.

    Returns:
        None.
    """

    for key in (
        f"climatogram_period_name_{index}",
        f"climatogram_period_{index}_date_from",
        f"climatogram_period_{index}_date_to",
    ):
        st.session_state.pop(key, None)


def _period_label(index: int, name: str | None, date_from: Any, date_to: Any) -> str:
    """Формирует подпись периода для графиков и таблиц.

    Args:
        index: Номер периода с нуля.
        name: Пользовательское название периода.
        date_from: Начальная дата периода.
        date_to: Конечная дата периода.

    Returns:
        Человекочитаемая подпись периода.
    """

    base = name.strip() if name else f"Период {index + 1}"
    if date_from and date_to:
        return f"{base}: {date_from.isoformat()} - {date_to.isoformat()}"
    return base


def _render_period_controls() -> None:
    """Отображает кнопки добавления и удаления периодов.

    Returns:
        None.
    """

    add_col, remove_col = st.columns(2)
    with add_col:
        if st.button("Добавить период", use_container_width=True):
            _clear_climatogram_results()
            st.session_state["climatogram_period_count"] = _period_count() + 1
            st.rerun()
    with remove_col:
        if st.button("Удалить последний", use_container_width=True, disabled=_period_count() <= 1):
            _clear_climatogram_results()
            _drop_period_state(_period_count() - 1)
            st.session_state["climatogram_period_count"] = max(1, _period_count() - 1)
            st.rerun()


def _render_periods() -> list[dict[str, Any]]:
    """Отображает динамический список периодов.

    Returns:
        Список выбранных периодов с датами и подписями.
    """

    _render_period_controls()
    periods = []
    for index in range(_period_count()):
        st.markdown(f"**Период {index + 1}**")
        name = st.text_input("Название периода", value=f"Период {index + 1}", key=f"climatogram_period_name_{index}")
        date_from, date_to = date_period(prefix=f"climatogram_period_{index}")
        periods.append(
            {
                "index": index,
                "name": name,
                "date_from": date_from,
                "date_to": date_to,
                "label": _period_label(index, name, date_from, date_to),
            }
        )
    return periods


def _climatogram_signature(
    selected_station_ids: list[Any],
    periods: list[dict[str, Any]],
    temperature_parameter: Any,
    precipitation_parameter: Any,
) -> tuple:
    """Формирует подпись текущих параметров климатограммы.

    Args:
        selected_station_ids: Выбранные метеостанции.
        periods: Список периодов.
        temperature_parameter: Параметр температуры.
        precipitation_parameter: Параметр осадков.

    Returns:
        Hashable-подпись текущего набора входных параметров.
    """

    return (
        tuple(str(item) for item in selected_station_ids),
        tuple(
            (
                period.get("date_from").isoformat() if period.get("date_from") else "",
                period.get("date_to").isoformat() if period.get("date_to") else "",
                period.get("name") or "",
            )
            for period in periods
        ),
        str(temperature_parameter),
        str(precipitation_parameter),
    )


def _color_key(station_identifier: Any, metric: str) -> str:
    """Возвращает ключ цвета для станции и показателя.

    Args:
        station_identifier: Идентификатор станции.
        metric: Код показателя.

    Returns:
        Строковый ключ цветовой карты.
    """

    return f"{station_identifier}:{metric}"


def _render_color_palette(stations: list[dict], selected_station_ids: list[Any]) -> dict[str, str]:
    """Отображает палитру цветов для температуры и осадков по станциям.

    Args:
        stations: Список станций из backend API.
        selected_station_ids: Выбранные метеостанции.

    Returns:
        Словарь цветов для графиков.
    """

    if not selected_station_ids:
        return {}

    by_id = _station_lookup(stations)
    color_map: dict[str, str] = {}
    with st.expander("Цвета графиков", expanded=False):
        st.caption("Цвет задаётся отдельно для температуры и осадков каждой метеостанции.")
        for index, current_station_id in enumerate(selected_station_ids):
            station = by_id.get(current_station_id, {"id": current_station_id, "name": f"Станция {current_station_id}"})
            st.markdown(f"**{station.get('name') or station_label(station)}**")
            temp_col, precip_col = st.columns(2)
            with temp_col:
                temperature_color = st.color_picker(
                    "Температура",
                    value=st.session_state.get(
                        f"climatogram_color_{current_station_id}_temperature",
                        TEMPERATURE_COLORS[index % len(TEMPERATURE_COLORS)],
                    ),
                    key=f"climatogram_color_{current_station_id}_temperature",
                )
            with precip_col:
                precipitation_color = st.color_picker(
                    "Осадки",
                    value=st.session_state.get(
                        f"climatogram_color_{current_station_id}_precipitation",
                        PRECIPITATION_COLORS[index % len(PRECIPITATION_COLORS)],
                    ),
                    key=f"climatogram_color_{current_station_id}_precipitation",
                )
            color_map[_color_key(current_station_id, "temperature")] = temperature_color
            color_map[_color_key(current_station_id, "precipitation")] = precipitation_color
    return color_map


def _validate_inputs(
    selected_station_ids: list[Any],
    periods: list[dict[str, Any]],
    temperature_parameter: Any,
    precipitation_parameter: Any,
) -> str | None:
    """Проверяет параметры построения нескольких климатограмм.

    Args:
        selected_station_ids: Выбранные метеостанции.
        periods: Список периодов.
        temperature_parameter: Параметр температуры.
        precipitation_parameter: Параметр осадков.

    Returns:
        Сообщение об ошибке или None.
    """

    if not selected_station_ids:
        return "Выберите хотя бы одну метеостанцию."
    if not periods:
        return "Добавьте хотя бы один период."
    if not temperature_parameter:
        return "Выберите параметр температуры."
    if not precipitation_parameter:
        return "Выберите параметр осадков."

    for period in periods:
        validation = validate_period(period.get("date_from"), period.get("date_to"))
        if not validation.ok:
            return f"{period.get('name') or 'Период'}: {validation.message}"
    return None


def _run_climatograms(
    stations: list[dict],
    selected_station_ids: list[Any],
    periods: list[dict[str, Any]],
    temperature_parameter: Any,
    precipitation_parameter: Any,
) -> tuple[list[dict[str, Any]], list[str]]:
    """Запрашивает климатограммы по всем выбранным станциям и периодам.

    Args:
        stations: Список станций из backend API.
        selected_station_ids: Выбранные метеостанции.
        periods: Список периодов.
        temperature_parameter: Параметр температуры.
        precipitation_parameter: Параметр осадков.

    Returns:
        Кортеж успешных результатов и текстовых ошибок.
    """

    by_id = _station_lookup(stations)
    items: list[dict[str, Any]] = []
    errors: list[str] = []

    for current_station_id in selected_station_ids:
        station = by_id.get(current_station_id, {"id": current_station_id, "name": f"Станция {current_station_id}"})
        for period in periods:
            payload = {
                "station_id": current_station_id,
                "date_from": period["date_from"].isoformat(),
                "date_to": period["date_to"].isoformat(),
                "temperature_parameter_id": temperature_parameter,
                "precipitation_parameter_id": precipitation_parameter,
            }
            try:
                result = analysis.run_climatogram(payload)
            except ApiError as error:
                errors.append(f"{station_label(station)} · {period['label']}: {error}")
                continue
            items.append(
                {
                    "station_id": current_station_id,
                    "station_name": station.get("name") or station_label(station),
                    "station_label": station_label(station),
                    "period_index": period["index"],
                    "period_label": period["label"],
                    "request": payload,
                    "result": result,
                }
            )
    return items, errors


def _table_rows(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Преобразует результаты климатограмм в строки таблицы.

    Args:
        items: Результаты климатограмм.

    Returns:
        Плоский список строк для таблицы.
    """

    rows = []
    for item in items:
        for month in unwrap_records(item.get("result"), ("months", "values", "data", "items")):
            rows.append(
                {
                    "Станция": item.get("station_name"),
                    "Период": item.get("period_label"),
                    "Месяц": month.get("month"),
                    "Температура": month.get("temperature_mean") if "temperature_mean" in month else month.get("temperature"),
                    "Осадки": month.get("precipitation_sum") if "precipitation_sum" in month else month.get("precipitation"),
                }
            )
    return rows


setup_page("Климатограмма")
init_session_state()
require_auth()
render_sidebar()
page_title("Климатограмма", "Температура и осадки по месяцам для нескольких метеостанций и периодов.")
render_home_button()

try:
    with st.sidebar:
        stations = load_stations()
        parameters = load_parameters()
        selected_station_ids = multiselect_stations(stations, "climatogram_stations")

        st.subheader("Периоды")
        periods = _render_periods()

        st.subheader("Параметры")
        temperature_parameter = select_parameter(parameters, "climatogram_temp", "Параметр температуры")
        precipitation_parameter = select_parameter(parameters, "climatogram_precip", "Параметр осадков")

        st.subheader("Режимы наложения")
        overlay_stations = st.checkbox("Накладывать метеостанции", value=True, key="climatogram_overlay_stations")
        overlay_periods = st.checkbox("Накладывать периоды", value=False, key="climatogram_overlay_periods")
        color_map = _render_color_palette(stations, selected_station_ids)

        combinations_count = len(selected_station_ids) * len(periods)
        if combinations_count > 24:
            st.warning(f"Будет построено {combinations_count} климатограмм. Запрос может занять больше времени.")

        run_clicked = st.button("Построить климатограммы", type="primary", use_container_width=True)
except ApiError as error:
    render_api_error(error)
    st.stop()

if run_clicked:
    validation_message = _validate_inputs(selected_station_ids, periods, temperature_parameter, precipitation_parameter)
    if validation_message:
        st.error(validation_message)
    else:
        try:
            with st.spinner("Backend строит климатограммы..."):
                items, errors = _run_climatograms(
                    stations,
                    selected_station_ids,
                    periods,
                    temperature_parameter,
                    precipitation_parameter,
                )
                st.session_state["last_climatogram_items"] = items
                st.session_state["last_climatogram_errors"] = errors
                st.session_state["last_climatogram_signature"] = _climatogram_signature(
                    selected_station_ids,
                    periods,
                    temperature_parameter,
                    precipitation_parameter,
                )
        except ApiError as error:
            render_api_error(error)

current_signature = _climatogram_signature(selected_station_ids, periods, temperature_parameter, precipitation_parameter)
stored_signature = st.session_state.get("last_climatogram_signature")
items = st.session_state.get("last_climatogram_items") or []
errors = st.session_state.get("last_climatogram_errors") or []

if items and stored_signature != current_signature:
    st.info("Параметры климатограммы изменились. Нажмите «Построить климатограммы», чтобы обновить таблицу и графики.")
    items = []
    errors = []

if errors:
    with st.expander("Ошибки по отдельным комбинациям", expanded=True):
        for error in errors:
            st.error(error)

if not items:
    st.info("Выберите метеостанции, добавьте один или несколько периодов и постройте климатограммы.")
    st.stop()

st.subheader("Климатограммы")
render_multi_climatograms(
    items,
    overlay_stations=overlay_stations,
    overlay_periods=overlay_periods,
    title="Климатограмма",
    color_map=color_map,
)

st.subheader("Таблица")
render_table(_table_rows(items))
render_json_preview({"items": items, "errors": errors}, "Полный JSON климатограмм")
