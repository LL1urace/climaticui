"""Map components."""

from __future__ import annotations

from html import escape
from typing import Any

import pandas as pd
import pydeck as pdk
import streamlit as st

from app.utils.formatters import station_id, station_label, unwrap_records


def _station_record_id(record: dict) -> Any:
    """Возвращает идентификатор станции для карты.

    Args:
        record: Запись метеостанции из backend API.

    Returns:
        Идентификатор станции, код или None.
    """

    return station_id(record) or record.get("code")


def _safe_display(value: Any, fallback: str = "n/a") -> str:
    """Форматирует значение станции для отображения в UI.

    Args:
        value: Значение поля станции.
        fallback: Строка, которая используется для пустых значений.

    Returns:
        Безопасная HTML-строка для вывода.
    """

    if value is None:
        return fallback
    try:
        if pd.isna(value):
            return fallback
    except (TypeError, ValueError):
        pass
    return escape(str(value))


def _get_event_value(source: Any, key: str) -> Any:
    """Читает значение из dict-подобного или объектного события Streamlit.

    Args:
        source: Событие, вложенный объект события или словарь.
        key: Имя поля для чтения.

    Returns:
        Значение поля или None.
    """

    if source is None:
        return None
    if isinstance(source, dict):
        return source.get(key)
    return getattr(source, key, None)


def _as_record(value: Any) -> dict | None:
    """Преобразует объект выбранной точки карты в словарь.

    Args:
        value: Объект из события выбора PyDeck.

    Returns:
        Словарь с данными выбранной точки или None.
    """

    if isinstance(value, dict):
        return value
    if hasattr(value, "to_dict"):
        result = value.to_dict()
        return result if isinstance(result, dict) else None
    return None


def _flatten_selection_objects(objects: Any) -> list[dict]:
    """Разворачивает выбранные объекты PyDeck в плоский список словарей.

    Args:
        objects: Поле objects из события выбора Streamlit.

    Returns:
        Список выбранных объектов карты.
    """

    if objects is None:
        return []
    if isinstance(objects, list):
        return [record for item in objects if (record := _as_record(item))]
    if isinstance(objects, dict):
        if any(key in objects for key in ("_station_id", "_station_source_id", "index")):
            record = _as_record(objects)
            return [record] if record else []
        records: list[dict] = []
        for value in objects.values():
            records.extend(_flatten_selection_objects(value))
        return records
    record = _as_record(objects)
    return [record] if record else []


def _extract_selected_objects(event: Any, frame: pd.DataFrame) -> list[dict]:
    """Извлекает выбранные пользователем точки из события карты.

    Args:
        event: Событие `st.pydeck_chart` после выбора точки.
        frame: DataFrame с данными слоя карты.

    Returns:
        Список записей выбранных станций.
    """

    selection = _get_event_value(event, "selection")
    objects = _get_event_value(selection, "objects")
    if objects is None:
        objects = _get_event_value(selection, "object")
    selected_objects = _flatten_selection_objects(objects)
    completed: list[dict] = []
    for item in selected_objects:
        index = item.get("index")
        if index is not None:
            try:
                completed.append(frame.iloc[int(index)].to_dict())
                continue
            except (IndexError, TypeError, ValueError):
                pass
        completed.append(item)
    return completed


def _selected_ids_from_objects(selected_objects: list[dict], id_lookup: dict[str, Any]) -> list[Any]:
    """Возвращает идентификаторы станций из выбранных объектов карты.

    Args:
        selected_objects: Объекты, выбранные пользователем на карте.
        id_lookup: Сопоставление строкового ID с исходным типом ID станции.

    Returns:
        Список идентификаторов станций без дублей.
    """

    selected_ids: list[Any] = []
    seen: set[str] = set()
    for item in selected_objects:
        raw_id = None
        for key in ("_station_id", "_station_source_id", "id", "station_id"):
            if key in item and item[key] not in (None, ""):
                raw_id = item[key]
                break
        if raw_id is None:
            continue
        key = str(raw_id)
        if key in seen:
            continue
        seen.add(key)
        selected_ids.append(id_lookup.get(key, raw_id))
    return selected_ids


def _render_map_selection_details(selected_objects: list[dict]) -> None:
    """Отображает краткую информацию о точках, выбранных на карте.

    Args:
        selected_objects: Объекты станций, выбранные пользователем.

    Returns:
        None.
    """

    if not selected_objects:
        return

    if len(selected_objects) == 1:
        station = selected_objects[0]
        st.markdown(
            f"""
            <div class="klima-card klima-card-ink">
                <h3>{_safe_display(station.get("name") or "Метеостанция")}</h3>
                <p><strong>Код:</strong> {_safe_display(station.get("code"))}</p>
                <p><strong>Регион:</strong> {_safe_display(station.get("country"))}, {_safe_display(station.get("region"))}</p>
                <p><strong>Координаты:</strong> {_safe_display(station.get("latitude"))}, {_safe_display(station.get("longitude"))}</p>
                <p><strong>Высота:</strong> {_safe_display(station.get("elevation"))} м</p>
            </div>
            """,
            unsafe_allow_html=True,
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
            "Высота": station.get("elevation"),
        }
        for station in selected_objects
    ]
    st.dataframe(pd.DataFrame(rows), hide_index=True, use_container_width=True)


def render_stations_map(
    payload: Any,
    value_key: str | None = None,
    selected_ids: list[Any] | None = None,
    selectable: bool = False,
    selection_key: str = "stations_map_selection",
    selection_mode: str = "multi-object",
    show_selection_details: bool = False,
    show_only_selected: bool = False,
) -> list[Any] | None:
    """Отображает карту станций через PyDeck.

    Args:
        payload: JSON-ответ или список станций с координатами.
        value_key: Поле значения для подсказки на карте.
        selected_ids: Идентификаторы станций, которые нужно выделить на карте.
        selectable: Включает выбор станций кликом по точкам карты.
        selection_key: Уникальный ключ интерактивной карты Streamlit.
        selection_mode: Режим выбора объектов PyDeck.
        show_selection_details: Отображает карточку с выбранными на карте станциями.
        show_only_selected: Скрывает все станции, кроме выбранных.

    Returns:
        Список идентификаторов выбранных на карте станций или None.
    """

    df = pd.DataFrame(unwrap_records(payload))
    if df.empty:
        st.info("Станции для карты отсутствуют.")
        return

    lat_col = "latitude" if "latitude" in df.columns else "lat"
    lon_col = "longitude" if "longitude" in df.columns else "lon"
    if lat_col not in df.columns or lon_col not in df.columns:
        st.warning("Backend не вернул координаты станций.")
        return

    df = df.dropna(subset=[lat_col, lon_col]).copy()
    if df.empty:
        st.warning("У выбранных станций нет координат.")
        return

    df["_station_source_id"] = df.apply(lambda row: _station_record_id(row.to_dict()), axis=1)
    df["_station_id"] = df["_station_source_id"].apply(lambda item: str(item) if item is not None else "")
    id_lookup = {
        str(source_id): source_id
        for source_id in df["_station_source_id"].tolist()
        if source_id is not None
    }
    selected = {str(item_id) for item_id in selected_ids or []}
    df["_selected"] = df["_station_id"].isin(selected)
    if show_only_selected:
        df = df[df["_selected"]].copy()
        if df.empty:
            st.info("Выберите станции, чтобы отобразить их на карте.")
            return None

    df["_color"] = df["_selected"].apply(lambda item: [245, 158, 11, 235] if item else [13, 100, 216, 165])
    df["_radius"] = 48000
    df["tooltip"] = df.apply(
        lambda row: (
            f"{_safe_display(row.get('name', 'Станция'))}<br>{_safe_display(value_key)}: {_safe_display(row.get(value_key))}"
            if value_key
            else _safe_display(row.get("name", "Станция"))
        ),
        axis=1,
    )
    layer = pdk.Layer(
        "ScatterplotLayer",
        id="stations-layer",
        data=df,
        get_position=[lon_col, lat_col],
        get_radius="_radius",
        get_fill_color="_color",
        pickable=True,
    )
    view_state = pdk.ViewState(latitude=float(df[lat_col].mean()), longitude=float(df[lon_col].mean()), zoom=3)
    deck = pdk.Deck(layers=[layer], initial_view_state=view_state, tooltip={"html": "{tooltip}"})

    if not selectable:
        st.pydeck_chart(deck)
        return None

    try:
        event = st.pydeck_chart(
            deck,
            key=selection_key,
            on_select="rerun",
            selection_mode=selection_mode,
            use_container_width=True,
        )
    except TypeError:
        st.pydeck_chart(deck)
        st.caption("Интерактивный выбор точек на карте недоступен в текущей версии Streamlit.")
        return None

    selected_objects = _extract_selected_objects(event, df)
    if show_selection_details:
        _render_map_selection_details(selected_objects)

    selected_from_map = _selected_ids_from_objects(selected_objects, id_lookup)
    return selected_from_map or None

