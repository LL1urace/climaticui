from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

import streamlit as st

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.api import comparisons
from app.api.client import ApiError
from app.components.charts import render_grouped_bar_chart
from app.components.errors import render_api_error
from app.components.filters import date_period, load_parameters, load_stations, multiselect_stations, select_aggregation, select_parameter
from app.components.layout import page_title, render_home_button, setup_page
from app.components.sidebar import render_sidebar
from app.components.tables import render_json_preview, render_table
from app.state.session import init_session_state, require_auth
from app.utils.formatters import station_id, station_label, unwrap_records
from app.utils.validators import periods_overlap, validate_period


STATION_COLORS = ["#0d64d8", "#17b6d6", "#f59e0b", "#16a34a", "#dc2626", "#7c3aed", "#0891b2", "#be123c"]


def _period_count() -> int:
    """Возвращает количество периодов для сравнения.

    Returns:
        Количество периодов из session state.
    """

    if "period_comparison_count" not in st.session_state:
        st.session_state["period_comparison_count"] = 2
    return int(st.session_state["period_comparison_count"])


def _clear_period_results() -> None:
    """Очищает сохранённые результаты сравнения периодов.

    Returns:
        None.
    """

    st.session_state["last_period_comparison"] = None
    st.session_state["last_period_comparison_errors"] = []
    st.session_state["last_period_comparison_signature"] = None


def _drop_period_state(index: int) -> None:
    """Удаляет состояние виджетов скрытого периода.

    Args:
        index: Индекс удалённого периода.

    Returns:
        None.
    """

    for key in (
        f"period_compare_name_{index}",
        f"period_compare_{index}_date_from",
        f"period_compare_{index}_date_to",
    ):
        st.session_state.pop(key, None)


def _period_label(index: int, name: str | None, date_from: Any, date_to: Any) -> str:
    """Формирует подпись периода.

    Args:
        index: Номер периода с нуля.
        name: Пользовательское название.
        date_from: Начальная дата.
        date_to: Конечная дата.

    Returns:
        Подпись периода.
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
            _clear_period_results()
            st.session_state["period_comparison_count"] = _period_count() + 1
            st.rerun()
    with remove_col:
        if st.button("Удалить последний", use_container_width=True, disabled=_period_count() <= 2):
            _clear_period_results()
            _drop_period_state(_period_count() - 1)
            st.session_state["period_comparison_count"] = max(2, _period_count() - 1)
            st.rerun()


def _render_periods() -> list[dict[str, Any]]:
    """Отображает динамический список периодов.

    Returns:
        Список периодов для сравнения.
    """

    _render_period_controls()
    periods = []
    for index in range(_period_count()):
        st.markdown(f"**Период {index + 1}**")
        name = st.text_input("Название периода", value=f"Период {index + 1}", key=f"period_compare_name_{index}")
        date_from, date_to = date_period(f"period_compare_{index}")
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


def _station_lookup(stations: list[dict]) -> dict[Any, dict]:
    """Возвращает справочник станций по идентификатору.

    Args:
        stations: Список станций из backend API.

    Returns:
        Словарь station_id -> запись станции.
    """

    return {station_id(station): station for station in stations}


def _render_station_palette(stations: list[dict], selected_station_ids: list[Any]) -> dict[str, str]:
    """Отображает выбор цветов станций для графика.

    Args:
        stations: Список станций из backend API.
        selected_station_ids: Выбранные станции.

    Returns:
        Словарь цветов по названию станции.
    """

    if not selected_station_ids:
        return {}

    by_id = _station_lookup(stations)
    colors: dict[str, str] = {}
    with st.expander("Цвета станций", expanded=False):
        for index, current_station_id in enumerate(selected_station_ids):
            station = by_id.get(current_station_id, {"id": current_station_id, "name": f"Станция {current_station_id}"})
            label = station.get("name") or station_label(station)
            colors[label] = st.color_picker(
                label,
                value=st.session_state.get(f"period_station_color_{current_station_id}", STATION_COLORS[index % len(STATION_COLORS)]),
                key=f"period_station_color_{current_station_id}",
            )
    return colors


def _comparison_signature(
    selected_station_ids: list[Any],
    parameter: Any,
    aggregation: str,
    periods: list[dict[str, Any]],
) -> tuple:
    """Формирует подпись текущих параметров сравнения.

    Args:
        selected_station_ids: Выбранные станции.
        parameter: Выбранный параметр.
        aggregation: Тип агрегации.
        periods: Список периодов.

    Returns:
        Hashable-подпись входных параметров.
    """

    return (
        tuple(str(item) for item in selected_station_ids),
        str(parameter),
        aggregation,
        tuple(
            (
                period.get("date_from").isoformat() if period.get("date_from") else "",
                period.get("date_to").isoformat() if period.get("date_to") else "",
                period.get("name") or "",
            )
            for period in periods
        ),
    )


def _validate_inputs(selected_station_ids: list[Any], parameter: Any, periods: list[dict[str, Any]]) -> str | None:
    """Проверяет параметры сравнения периодов.

    Args:
        selected_station_ids: Выбранные станции.
        parameter: Выбранный параметр.
        periods: Список периодов.

    Returns:
        Сообщение об ошибке или None.
    """

    if not selected_station_ids:
        return "Выберите хотя бы одну метеостанцию."
    if not parameter:
        return "Выберите параметр."
    if len(periods) < 2:
        return "Добавьте минимум два периода."
    for period in periods:
        validation = validate_period(period.get("date_from"), period.get("date_to"))
        if not validation.ok:
            return f"{period.get('name') or 'Период'}: {validation.message}"
    return None


def _period_overlap_messages(periods: list[dict[str, Any]]) -> list[str]:
    """Возвращает предупреждения о пересекающихся периодах.

    Args:
        periods: Список периодов.

    Returns:
        Список текстовых предупреждений.
    """

    messages = []
    for first_index, first in enumerate(periods):
        for second in periods[first_index + 1 :]:
            if periods_overlap(first["date_from"], first["date_to"], second["date_from"], second["date_to"]):
                messages.append(f"{first['name']} пересекается с {second['name']}.")
    return messages


def _period_record(station: dict, period: dict[str, Any], source: dict) -> dict[str, Any]:
    """Нормализует запись статистики периода.

    Args:
        station: Запись станции.
        period: Описание периода.
        source: Запись backend со статистиками.

    Returns:
        Строка таблицы сравнения.
    """

    ignored = {"values", "series", "data", "items"}
    row = {key: value for key, value in source.items() if key not in ignored}
    row.update(
        {
            "station_id": station_id(station),
            "station_name": station.get("name") or station_label(station),
            "period_index": period["index"],
            "period": period["label"],
        }
    )
    return row


def _run_period_comparisons(
    stations: list[dict],
    selected_station_ids: list[Any],
    parameter: Any,
    aggregation: str,
    periods: list[dict[str, Any]],
) -> tuple[dict[str, list[dict[str, Any]]], list[str]]:
    """Запускает сравнения всех периодов относительно первого.

    Args:
        stations: Список станций из backend API.
        selected_station_ids: Выбранные станции.
        parameter: Выбранный параметр.
        aggregation: Тип агрегации.
        periods: Список периодов.

    Returns:
        Результаты и ошибки по отдельным запросам.
    """

    by_id = _station_lookup(stations)
    baseline = periods[0]
    rows: list[dict[str, Any]] = []
    differences: list[dict[str, Any]] = []
    raw_results: list[dict[str, Any]] = []
    errors: list[str] = []

    for current_station_id in selected_station_ids:
        station = by_id.get(current_station_id, {"id": current_station_id, "name": f"Станция {current_station_id}"})
        baseline_added = False
        for target in periods[1:]:
            payload = {
                "station_id": current_station_id,
                "parameter_id": parameter,
                "aggregation": aggregation,
                "period_1": {"date_from": baseline["date_from"].isoformat(), "date_to": baseline["date_to"].isoformat()},
                "period_2": {"date_from": target["date_from"].isoformat(), "date_to": target["date_to"].isoformat()},
            }
            try:
                result = comparisons.compare_periods(payload)
            except ApiError as error:
                errors.append(f"{station_label(station)} · {target['label']}: {error}")
                continue

            period_rows = unwrap_records(result, ("periods", "results", "data", "items"))
            if period_rows:
                if not baseline_added:
                    rows.append(_period_record(station, baseline, period_rows[0]))
                    baseline_added = True
                if len(period_rows) > 1:
                    rows.append(_period_record(station, target, period_rows[1]))

            difference = result.get("difference") or result.get("diff") or {}
            if isinstance(difference, dict):
                differences.append(
                    {
                        "station_name": station.get("name") or station_label(station),
                        "baseline": baseline["label"],
                        "period": target["label"],
                        **difference,
                    }
                )
            raw_results.append({"station_id": current_station_id, "target_period": target["label"], "result": result})

    return {"periods": rows, "differences": differences, "raw": raw_results}, errors


setup_page("Сравнение периодов")
init_session_state()
require_auth()
render_sidebar()
page_title("Сравнение периодов", "Сравнивайте несколько периодов для одной или нескольких метеостанций.")
render_home_button()

try:
    with st.sidebar:
        st.header("Параметры")
        stations = load_stations()
        parameters = load_parameters()
        selected_station_ids = multiselect_stations(stations, "period_comparison_stations")
        parameter = select_parameter(parameters, key="period_comparison_parameter")
        aggregation = select_aggregation("period_comparison_aggregation")
        metric = st.selectbox("Метрика графика", ["mean", "min", "max", "std", "sum"], key="period_comparison_metric")
        station_colors = _render_station_palette(stations, selected_station_ids)

        st.subheader("Периоды")
        periods = _render_periods()
        run_clicked = st.button("Сравнить периоды", type="primary", use_container_width=True)
except ApiError as error:
    render_api_error(error)
    st.stop()

for message in _period_overlap_messages(periods):
    st.warning(message)

if run_clicked:
    validation_message = _validate_inputs(selected_station_ids, parameter, periods)
    if validation_message:
        st.error(validation_message)
    else:
        try:
            with st.spinner("Backend сравнивает периоды..."):
                result, errors = _run_period_comparisons(
                    stations,
                    selected_station_ids,
                    parameter,
                    aggregation,
                    periods,
                )
                st.session_state["last_period_comparison"] = result
                st.session_state["last_period_comparison_errors"] = errors
                st.session_state["last_period_comparison_signature"] = _comparison_signature(
                    selected_station_ids,
                    parameter,
                    aggregation,
                    periods,
                )
        except ApiError as error:
            render_api_error(error)

current_signature = _comparison_signature(selected_station_ids, parameter, aggregation, periods)
stored_signature = st.session_state.get("last_period_comparison_signature")
result = st.session_state.get("last_period_comparison")
errors = st.session_state.get("last_period_comparison_errors") or []
if result and stored_signature != current_signature:
    st.info("Параметры сравнения изменились. Нажмите «Сравнить периоды», чтобы обновить таблицу и график.")
    result = None
    errors = []

if errors:
    with st.expander("Ошибки по отдельным сравнениям", expanded=True):
        for error in errors:
            st.error(error)

if not result:
    st.info("Выберите станции, добавьте периоды и запустите сравнение.")
    st.stop()

period_rows = result.get("periods") or []
differences = result.get("differences") or []

st.subheader("Разница относительно базового периода")
render_table(differences, empty_message="Разницы периодов отсутствуют.")
st.subheader("Таблица сравнения")
render_table(period_rows, empty_message="Данные сравнения отсутствуют.")
st.subheader("График сравнения")
render_grouped_bar_chart(
    period_rows,
    x_key="period",
    y_key=metric,
    group_key="station_name",
    title=f"{metric}: значения по периодам",
    color_map=station_colors,
)
render_json_preview({"result": result, "errors": errors}, "Полный JSON сравнения")
