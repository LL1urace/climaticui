from __future__ import annotations

import csv
from datetime import date, datetime
import io
import sys
from pathlib import Path
from typing import Any

import streamlit as st

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.api import observations, saved_sets
from app.api.client import ApiError
from app.components.errors import render_api_error
from app.components.layout import page_title, render_home_button, setup_page
from app.components.saved_set_modes import SAVE_SET_MODE_ORDER, format_modes, mode_label, normalize_saved_set_modes
from app.components.sidebar import render_sidebar
from app.components.tables import render_json_preview, render_table
from app.data_sources.local_observations import local_raw_observation_rows
from app.state.session import init_session_state, require_auth, restore_saved_analysis_set
from app.utils.formatters import format_date, unwrap_records


def _record_id(record: dict[str, Any]) -> Any:
    """Возвращает идентификатор сохранённого набора."""

    return record.get("id") or record.get("saved_set_id") or record.get("analysis_set_id")


def _as_list(value: Any) -> list[Any]:
    """Нормализует поле сохранённого набора в список."""

    if value is None:
        return []
    return value if isinstance(value, list) else [value]


def _identifier(value: Any, keys: tuple[str, ...]) -> Any:
    """Returns a plain identifier from a scalar or dictionary value."""

    if isinstance(value, dict):
        for key in keys:
            if value.get(key) not in (None, ""):
                return value[key]
        return None
    return value


def _unique_values(values: list[Any]) -> list[Any]:
    """Keeps values unique while preserving order."""

    result = []
    seen = set()
    for value in values:
        if value in (None, ""):
            continue
        marker = str(value)
        if marker in seen:
            continue
        seen.add(marker)
        result.append(value)
    return result


def _record_snapshot(record: dict[str, Any]) -> dict[str, Any]:
    """Returns saved parameter snapshot from a record, if present."""

    for key in ("session_snapshot", "parameters_snapshot", "extra_parameters", "persisted_form_values"):
        snapshot = record.get(key)
        if isinstance(snapshot, dict):
            return snapshot
    return {}


def _record_station_ids(record: dict[str, Any]) -> list[Any]:
    """Returns station ids saved in a record."""

    snapshot = _record_snapshot(record)
    station_values = _as_list(
        snapshot.get("dashboard_station_ids")
        or snapshot.get("dashboard_station_multiselect")
        or record.get("station_ids")
        or record.get("selected_station_ids")
        or record.get("selected_stations")
    )
    station_id = record.get("station_id") or record.get("station") or record.get("stationId")
    if station_id not in (None, ""):
        station_values.append(station_id)
    return _unique_values([_identifier(item, ("id", "station_id", "stationId")) for item in station_values])


def _record_parameter_ids(record: dict[str, Any]) -> list[Any]:
    """Returns parameter ids saved in a record."""

    snapshot = _record_snapshot(record)
    parameter_values = _as_list(
        snapshot.get("dashboard_parameter_ids")
        or snapshot.get("dashboard_parameters")
        or record.get("selected_parameters")
        or record.get("parameter_ids")
        or record.get("parameters")
    )
    parameter_id = record.get("parameter_id") or record.get("parameter") or record.get("parameterId")
    if parameter_id not in (None, ""):
        parameter_values.append(parameter_id)
    return _unique_values([_identifier(item, ("id", "parameter_id", "parameterId")) for item in parameter_values])


def _record_modes(record: dict[str, Any]) -> list[str]:
    """Returns normalized scenario codes for a saved set."""

    return normalize_saved_set_modes(record, fallback=record.get("mode"))


def _date_param(value: Any) -> str:
    """Returns an ISO date string for API params and filenames."""

    return format_date(value)[:10]


def _period_label(record: dict[str, Any]) -> str:
    """Формирует подпись периода сохранённого набора."""

    start = record.get("period_start") or record.get("date_from")
    end = record.get("period_end") or record.get("date_to")
    return f"{format_date(start)} - {format_date(end)}" if start or end else "Период не задан"


def _created_sort_key(record: dict[str, Any]) -> float:
    """Возвращает дату создания для сортировки."""

    value = record.get("created_at") or record.get("updated_at")
    if isinstance(value, datetime):
        return value.timestamp()
    if isinstance(value, str):
        try:
            return datetime.fromisoformat(value.replace("Z", "+00:00")).timestamp()
        except ValueError:
            return 0.0
    return 0.0


def _saved_set_label(record: dict[str, Any]) -> str:
    """Формирует человекочитаемую подпись сохранённого набора."""

    record_id = _record_id(record) or "без ID"
    station = record.get("station_id") or record.get("station") or "станция не задана"
    parameter = record.get("parameter_id") or record.get("parameter") or "параметр не задан"
    modes = format_modes(_record_modes(record))
    created = format_date(record.get("created_at"))
    created_part = f" · {created}" if created else ""
    return f"#{record_id}: станция {station}, параметр {parameter}, {_period_label(record)} · {modes}{created_part}"


def _history_rows(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Подготавливает строки таблицы истории сохранённых наборов."""

    rows = []
    for record in records:
        rows.append(
            {
                "ID": _record_id(record),
                "Станция": record.get("station_id"),
                "Параметр": record.get("parameter_id"),
                "Показатели": ", ".join(str(item) for item in _as_list(record.get("selected_parameters"))),
                "Период": _period_label(record),
                "Агрегация": record.get("aggregation") or "monthly",
                "Сценарии": format_modes(_record_modes(record)),
                "Создан": format_date(record.get("created_at")),
            }
        )
    return rows


def _can_export_period_slice(record: dict[str, Any]) -> bool:
    """Checks whether a saved set has enough fields for CSV export."""

    return bool(
        _record_station_ids(record)
        and _record_parameter_ids(record)
        and _date_param(record.get("period_start") or record.get("date_from"))
        and _date_param(record.get("period_end") or record.get("date_to"))
    )


def _period_slice_filename(record: dict[str, Any]) -> str:
    """Builds a stable CSV filename for a saved set."""

    record_id = _record_id(record) or "selected"
    start = _date_param(record.get("period_start") or record.get("date_from")) or "start"
    end = _date_param(record.get("period_end") or record.get("date_to")) or "end"
    return f"climate_slice_set_{record_id}_{start}_{end}.csv"


def _period_slice_csv(record: dict[str, Any]) -> bytes:
    """Downloads timeseries rows for the saved set and serializes them to CSV."""

    station_ids = _record_station_ids(record)
    parameter_ids = _record_parameter_ids(record)
    date_from = _date_param(record.get("period_start") or record.get("date_from"))
    date_to = _date_param(record.get("period_end") or record.get("date_to"))
    aggregation = record.get("aggregation") or "monthly"

    output = io.StringIO()
    writer = csv.DictWriter(
        output,
        fieldnames=[
            "station_id",
            "station_name",
            "parameter_id",
            "aggregation",
            "period_start",
            "period_end",
            "date",
            "value",
            "value_column",
            "quality_flag",
            "source_name",
            "source_url",
            "error",
        ],
    )
    writer.writeheader()
    for station_id in station_ids:
        for parameter_id in parameter_ids:
            try:
                if aggregation == "raw":
                    rows = local_raw_observation_rows(station_id, parameter_id, date_from, date_to)
                    if not rows:
                        series = observations.get_raw_observations(station_id, parameter_id, date_from, date_to)
                        rows = unwrap_records(series, ("values", "series", "data", "items", "records"))
                else:
                    series = observations.get_timeseries(station_id, parameter_id, date_from, date_to, aggregation)
                    rows = unwrap_records(series, ("values", "series", "data", "items", "records"))
            except ApiError as error:
                writer.writerow(
                    {
                        "station_id": station_id,
                        "station_name": "",
                        "parameter_id": parameter_id,
                        "aggregation": aggregation,
                        "period_start": date_from,
                        "period_end": date_to,
                        "date": "",
                        "value": "",
                        "value_column": "",
                        "quality_flag": "",
                        "source_name": "",
                        "source_url": "",
                        "error": str(error),
                    }
                )
                continue
            for row in rows:
                writer.writerow(
                    {
                        "station_id": station_id,
                        "station_name": row.get("station_name") or row.get("name") or "",
                        "parameter_id": parameter_id,
                        "aggregation": aggregation,
                        "period_start": date_from,
                        "period_end": date_to,
                        "date": row.get("date") or row.get("observed_at") or row.get("timestamp"),
                        "value": row.get("value") if row.get("value") is not None else row.get("y"),
                        "value_column": row.get("value_column") or "",
                        "quality_flag": row.get("quality_flag") or "",
                        "source_name": row.get("source_name") or "",
                        "source_url": row.get("source_url") or row.get("monthly_url") or "",
                        "error": "",
                    }
                )
    return output.getvalue().encode("utf-8-sig")


def _restore_summary(restored: dict[str, Any]) -> str:
    """Формирует текст о восстановленных параметрах."""

    period = ""
    if isinstance(restored.get("date_from"), date) or isinstance(restored.get("date_to"), date):
        period = f", период {format_date(restored.get('date_from'))} - {format_date(restored.get('date_to'))}"
    return (
        f"Восстановлено: станции {', '.join(str(item) for item in restored.get('station_ids') or [])}, "
        f"параметр {restored.get('parameter_id')}, агрегация {restored.get('aggregation')}{period}."
    )


setup_page("История анализов")
init_session_state()
require_auth()
render_sidebar()
page_title("История анализов", "Сохранённые пользователем наборы параметров для повторного анализа.")
render_home_button()

try:
    with st.spinner("Загружаю сохранённые наборы..."):
        saved_response = saved_sets.get_saved_analysis_sets()
except ApiError as error:
    render_api_error(error)
    st.stop()

records = sorted(unwrap_records(saved_response), key=_created_sort_key, reverse=True)
if not records:
    st.info("История пуста. Она появится, когда вы сохраните набор анализа на исследовательской панели.")
    st.stop()

modes_in_records = []
for mode in SAVE_SET_MODE_ORDER:
    if any(mode in _record_modes(record) for record in records):
        modes_in_records.append(mode)
for record in records:
    for mode in _record_modes(record):
        if mode not in modes_in_records:
            modes_in_records.append(mode)

with st.container(border=True, key="history_parameters"):
    st.subheader("Сохранённые наборы")
    selected_mode = st.selectbox(
        "Сценарий набора",
        ["all"] + modes_in_records,
        format_func=lambda item: "Все" if item == "all" else mode_label(item),
    )
    visible_records = [
        record
        for record in records
        if selected_mode == "all" or selected_mode in _record_modes(record)
    ]
    if visible_records:
        selected_index = st.selectbox(
            "Набор для восстановления",
            options=list(range(len(visible_records))),
            format_func=lambda index: _saved_set_label(visible_records[index]),
        )
        selected_record = visible_records[selected_index]
    else:
        st.info("Для выбранного режима сохранённых наборов нет.")
        selected_record = None
    restore_clicked = st.button(
        "Восстановить параметры набора",
        type="primary",
        use_container_width=True,
        disabled=selected_record is None,
    )
    if selected_record is not None:
        if _can_export_period_slice(selected_record):
            st.caption(
                "CSV выгружает сохранённый период набора. Для raw берутся исходные точки без месячного "
                "или годового укрупнения; monthly/yearly возвращают агрегированный ряд."
            )
            st.download_button(
                "Скачать срез периода CSV",
                data=_period_slice_csv(selected_record),
                file_name=_period_slice_filename(selected_record),
                mime="text/csv",
                use_container_width=True,
            )
        else:
            st.caption("CSV-срез недоступен: в наборе не хватает станции, показателя или периода.")

render_table(_history_rows(visible_records), empty_message="Сохранённые наборы отсутствуют.")

if restore_clicked and selected_record is not None:
    restored = restore_saved_analysis_set(selected_record)
    st.session_state["history_restore_summary"] = _restore_summary(restored)

if st.session_state.get("history_restore_summary"):
    st.success(st.session_state["history_restore_summary"])
    st.info("Теперь эти параметры будут подставлены на исследовательской панели и страницах анализа.")
    dashboard_column, analysis_column = st.columns(2)
    with dashboard_column:
        if st.button("Открыть исследовательскую панель", use_container_width=True):
            st.switch_page("pages/00_Dashboard.py")
    with analysis_column:
        if st.button("Открыть страницу анализа", use_container_width=True):
            st.switch_page("pages/01_Analysis.py")

if selected_record:
    render_json_preview(selected_record, "JSON сохранённого набора")
