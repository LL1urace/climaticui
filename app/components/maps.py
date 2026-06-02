"""Map components."""

from __future__ import annotations

import json
import math
from html import escape
from typing import Any
from urllib.parse import quote

import pandas as pd
import pydeck as pdk
import streamlit as st

from app.utils.formatters import station_id, station_label, unwrap_records


REAL_DATA_FLAGS = {"real_monthly", "sample_builtin", "builtin_real"}
SYNTHETIC_SAMPLE_COLOR = [6, 34, 69, 170]
REFERENCE_DATA_COLOR = [74, 149, 255, 165]
SELECTED_STATION_COLOR = [245, 158, 11, 235]
CLASSIFICATION_MISSING_COLOR = [100, 116, 139, 145]
CLASSIFICATION_GRADIENTS = {
    "climate": {
        "label": "Климатический: синий → бирюзовый → оранжевый",
        "stops": [[13, 100, 216], [23, 182, 214], [118, 228, 197], [255, 176, 32], [234, 88, 12]],
    },
    "cool_warm": {
        "label": "Контрастный: синий → светлый → красный",
        "stops": [[37, 99, 235], [147, 197, 253], [241, 245, 249], [253, 186, 116], [220, 38, 38]],
    },
    "forest": {
        "label": "Природный: зелёный → жёлтый → бордовый",
        "stops": [[5, 150, 105], [110, 231, 183], [254, 240, 138], [251, 146, 60], [159, 18, 57]],
    },
    "violet": {
        "label": "Спектральный: фиолетовый → голубой → розовый",
        "stops": [[91, 33, 182], [59, 130, 246], [34, 211, 238], [244, 114, 182], [190, 24, 93]],
    },
}
CLASSIFICATION_GRADIENT_LABELS = {
    gradient_name: gradient["label"]
    for gradient_name, gradient in CLASSIFICATION_GRADIENTS.items()
}
CLASSIFICATION_GRADIENT_STOPS = CLASSIFICATION_GRADIENTS["climate"]["stops"]
STATION_POINT_RADIUS = 34000
EURASIA_MAP_VIEW = {"latitude": 52.0, "longitude": 75.0, "zoom": 1.6, "pitch": 0, "bearing": 0}
CARTO_VOYAGER_STYLE = "https://basemaps.cartocdn.com/gl/voyager-gl-style/style.json"
CARTO_POSITRON_STYLE = "https://basemaps.cartocdn.com/gl/positron-gl-style/style.json"
CARTO_DARK_MATTER_STYLE = "https://basemaps.cartocdn.com/gl/dark-matter-gl-style/style.json"
ESRI_WORLD_IMAGERY_TILES = "https://services.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}"
ESRI_WORLD_TOPO_TILES = "https://services.arcgisonline.com/ArcGIS/rest/services/World_Topo_Map/MapServer/tile/{z}/{y}/{x}"
LOCAL_MAP_ASSETS_URL = "/app/static/maps"
OFFLINE_SATELLITE_IMAGE = f"{LOCAL_MAP_ASSETS_URL}/blue_marble_satellite_mercator.jpg"
OFFLINE_RELIEF_IMAGE = f"{LOCAL_MAP_ASSETS_URL}/natural_earth_relief_mercator.jpg"
BASEMAP_LABELS = {
    "dark_matter": "CARTO Dark Matter: тёмная (по умолчанию)",
    "voyager": "CARTO Voyager: цветная",
    "positron": "CARTO Positron: светлая",
    "satellite": "Esri World Imagery: спутниковая (онлайн)",
    "topographic": "Esri World Topographic: рельеф (онлайн)",
    "satellite_local": "NASA Blue Marble: спутниковая (локальная)",
    "topographic_local": "Natural Earth: рельеф (локальная)",
}


def _hex_to_rgba(value: str, alpha: int) -> list[int]:
    """Преобразует HEX-цвет в RGBA для PyDeck.

    Args:
        value: Цвет в формате `#RRGGBB`.
        alpha: Прозрачность точки от 0 до 255.

    Returns:
        RGBA-цвет или чёрный цвет с указанной прозрачностью для неверного HEX.
    """

    normalized = str(value or "").lstrip("#")
    if len(normalized) != 6:
        return [0, 0, 0, alpha]
    try:
        return [int(normalized[index : index + 2], 16) for index in (0, 2, 4)] + [alpha]
    except ValueError:
        return [0, 0, 0, alpha]


def _raster_map_style_url(tile_url: str, attribution: str) -> str:
    """Формирует строковый data URL MapLibre-стиля для raster-подложки.

    Args:
        tile_url: Шаблон URL тайлов с координатами `{z}`, `{y}` и `{x}`.
        attribution: Подпись источника картографических данных.

    Returns:
        Data URL со стилем карты и raster-источником.
    """

    style = {
        "version": 8,
        "sources": {
            "basemap": {
                "type": "raster",
                "tiles": [tile_url],
                "tileSize": 256,
                "attribution": attribution,
            }
        },
        "layers": [{"id": "basemap", "type": "raster", "source": "basemap"}],
    }
    return f"data:application/json;charset=utf-8,{quote(json.dumps(style, ensure_ascii=False, separators=(',', ':')))}"


def _background_map_style_url(background_color: str) -> str:
    """Формирует локальный MapLibre-стиль без сетевых источников данных.

    Args:
        background_color: HEX-цвет фона карты.

    Returns:
        Data URL со встроенным стилем и однотонным фоном.
    """

    style = {
        "version": 8,
        "sources": {},
        "layers": [
            {
                "id": "background",
                "type": "background",
                "paint": {"background-color": background_color},
            }
        ],
    }
    return f"data:application/json;charset=utf-8,{quote(json.dumps(style, ensure_ascii=False, separators=(',', ':')))}"


def map_basemap_configuration(basemap: str | None) -> tuple[str | None, str | None]:
    """Возвращает стиль и провайдер выбранной подложки карты."""

    if basemap == "positron":
        return CARTO_POSITRON_STYLE, "carto"

    if basemap == "voyager":
        return CARTO_VOYAGER_STYLE, "carto"

    if basemap == "satellite":
        return _raster_map_style_url(ESRI_WORLD_IMAGERY_TILES, "Tiles © Esri"), "carto"

    if basemap == "topographic":
        return _raster_map_style_url(ESRI_WORLD_TOPO_TILES, "Tiles © Esri"), "carto"

    if basemap in {"satellite_local", "topographic_local"}:
        return _background_map_style_url("#07111f"), "carto"

    return CARTO_DARK_MATTER_STYLE, "carto"


OFFLINE_MAP_IMAGES = {
    "satellite_local": OFFLINE_SATELLITE_IMAGE,
    "topographic_local": OFFLINE_RELIEF_IMAGE,
}


def map_basemap_layers(basemap: str | None) -> list[pdk.Layer]:
    """Создаёт дополнительные слои для локальных подложек карты."""

    image_url = OFFLINE_MAP_IMAGES.get(str(basemap or ""))

    if not image_url:
        return []

    return [
        pdk.Layer(
            "BitmapLayer",
            id=f"{basemap}-bitmap-layer",
            image=f'"{image_url}"',
            bounds=[-180, -85.051129, 180, 85.051129],
            opacity=1.0,
            pickable=False,
        )
    ]


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


def _has_real_station_data(record: dict) -> bool:
    """Проверяет, есть ли у станции реальные данные в sample-режиме.

    Args:
        record: Запись метеостанции для карты.

    Returns:
        True, если станция помечена как имеющая реальные monthly-данные.
    """

    if record.get("data_quality") in REAL_DATA_FLAGS:
        return True
    if str(record.get("quality_flag") or "").lower() in REAL_DATA_FLAGS:
        return True
    return bool(record.get("has_real_monthly_data"))


def classification_gradient_css(gradient_name: str | None = None) -> str:
    """Возвращает CSS-цвета выбранного градиента карты."""

    gradient = CLASSIFICATION_GRADIENTS.get(gradient_name or "climate", CLASSIFICATION_GRADIENTS["climate"])
    return ",".join(f"rgb({red},{green},{blue})" for red, green, blue in gradient["stops"])


def station_classification_color(
    value: Any,
    min_value: Any,
    max_value: Any,
    alpha: int = 210,
    gradient_name: str | None = None,
) -> list[int]:
    """Возвращает RGBA-цвет значения на градиенте классификации карты.

    Args:
        value: Среднее значение климатического параметра станции.
        min_value: Минимум среди классифицированных станций.
        max_value: Максимум среди классифицированных станций.
        alpha: Прозрачность точки от 0 до 255.
        gradient_name: Код цветовой палитры классификации.

    Returns:
        Интерполированный цвет или нейтральный цвет для отсутствующего значения.
    """

    try:
        number = float(value)
        lower = float(min_value)
        upper = float(max_value)
    except (TypeError, ValueError):
        return CLASSIFICATION_MISSING_COLOR
    if not all(math.isfinite(item) for item in (number, lower, upper)):
        return CLASSIFICATION_MISSING_COLOR

    ratio = 0.5 if upper <= lower else max(0.0, min(1.0, (number - lower) / (upper - lower)))
    gradient = CLASSIFICATION_GRADIENTS.get(gradient_name or "climate", CLASSIFICATION_GRADIENTS["climate"])
    stops = gradient["stops"]
    scaled = ratio * (len(stops) - 1)
    start_index = min(int(math.floor(scaled)), len(stops) - 1)
    end_index = min(start_index + 1, len(stops) - 1)
    fraction = scaled - start_index
    start = stops[start_index]
    end = stops[end_index]
    return [round(start[channel] + (end[channel] - start[channel]) * fraction) for channel in range(3)] + [alpha]


def _station_color(
    record: dict,
    color_map: dict[str, list[int]] | None = None,
    classification: dict[str, Any] | None = None,
) -> list[int]:
    """Возвращает цвет точки станции на карте.

    Args:
        record: Запись станции с флагом `_selected`.
        color_map: Необязательные RGBA-цвета трёх типов станций.
        classification: Необязательные настройки градиентной классификации.

    Returns:
        RGBA-цвет для PyDeck.
    """

    palette = color_map or {}
    if classification and classification.get("value_key"):
        return station_classification_color(
            record.get(classification["value_key"]),
            classification.get("min_value"),
            classification.get("max_value"),
            gradient_name=classification.get("gradient_name"),
        )
    if record.get("_selected"):
        return palette.get("selected", SELECTED_STATION_COLOR)
    if _has_real_station_data(record):
        return palette.get("real", REFERENCE_DATA_COLOR)
    return palette.get("synthetic", SYNTHETIC_SAMPLE_COLOR)


def station_map_palette(
    selected_color: str,
    real_color: str,
    synthetic_color: str,
) -> dict[str, list[int]]:
    """Формирует RGBA-палитру точек карты из цветов интерфейса.

    Args:
        selected_color: Цвет выбранных станций.
        real_color: Цвет станций с реальными данными.
        synthetic_color: Цвет станций со сгенерированными данными.

    Returns:
        Словарь RGBA-цветов для компонента карты.
    """

    return {
        "selected": _hex_to_rgba(selected_color, SELECTED_STATION_COLOR[3]),
        "real": _hex_to_rgba(real_color, REFERENCE_DATA_COLOR[3]),
        "synthetic": _hex_to_rgba(synthetic_color, SYNTHETIC_SAMPLE_COLOR[3]),
    }


def map_view_for_points(
    latitudes: list[float],
    longitudes: list[float],
) -> dict[str, float]:
    """Рассчитывает центр и масштаб карты для показа всех переданных точек.

    Args:
        latitudes: Широты видимых метеостанций.
        longitudes: Долготы видимых метеостанций.

    Returns:
        Настройки центра, масштаба, наклона и поворота карты.
    """

    if not latitudes or not longitudes:
        return dict(EURASIA_MAP_VIEW)
    latitude = sum(latitudes) / len(latitudes)
    longitude = sum(longitudes) / len(longitudes)
    if len(latitudes) == 1 or len(longitudes) == 1:
        zoom = 5.0
    else:
        latitude_span = max(latitudes) - min(latitudes)
        longitude_span = max(longitudes) - min(longitudes)
        longitude_scale = max(math.cos(math.radians(latitude)), 0.2)
        fitted_span = max(latitude_span, longitude_span * longitude_scale, 0.01)
        zoom = max(1.0, min(6.0, math.log2(150 / (fitted_span * 1.7))))
    return {
        "latitude": latitude,
        "longitude": longitude,
        "zoom": zoom,
        "pitch": 0,
        "bearing": 0,
    }



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
    value_label: str | None = None,
    selected_ids: list[Any] | None = None,
    selectable: bool = False,
    selection_key: str = "stations_map_selection",
    selection_mode: str = "multi-object",
    show_selection_details: bool = False,
    show_only_selected: bool = False,
    initial_view_state: dict[str, Any] | None = None,
    color_map: dict[str, list[int]] | None = None,
    classification: dict[str, Any] | None = None,
    fit_visible_points: bool = False,
    basemap: str = "dark_matter",
) -> list[Any] | None:
    """Отображает карту станций через PyDeck.

    Args:
        payload: JSON-ответ или список станций с координатами.
        value_key: Поле значения для подсказки на карте.
        value_label: Подпись значения для подсказки на карте.
        selected_ids: Идентификаторы станций, которые нужно выделить на карте.
        selectable: Включает выбор станций кликом по точкам карты.
        selection_key: Уникальный ключ интерактивной карты Streamlit.
        selection_mode: Режим выбора объектов PyDeck.
        show_selection_details: Отображает карточку с выбранными на карте станциями.
        show_only_selected: Скрывает все станции, кроме выбранных.
        initial_view_state: Начальный вид карты PyDeck.
        color_map: Необязательные RGBA-цвета выбранных, реальных и сгенерированных станций.
        classification: Настройки градиентной окраски точек по числовому полю.
        fit_visible_points: Подбирает центр и масштаб для всех отображаемых точек.
        basemap: Код подложки карты.

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

    df["_color"] = df.apply(lambda row: _station_color(row.to_dict(), color_map, classification), axis=1)
    df["_radius"] = STATION_POINT_RADIUS
    df["tooltip"] = df.apply(
        lambda row: (
            f"{_safe_display(row.get('name', 'Станция'))}<br>{_safe_display(value_label or value_key)}: {_safe_display(row.get(value_key))}"
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
    fitted_view_state = map_view_for_points(df[lat_col].tolist(), df[lon_col].tolist()) if fit_visible_points else {}
    effective_view_state = fitted_view_state or initial_view_state or {}
    view_state = pdk.ViewState(
        latitude=float(effective_view_state.get("latitude", df[lat_col].mean())),
        longitude=float(effective_view_state.get("longitude", df[lon_col].mean())),
        zoom=float(effective_view_state.get("zoom", 3)),
        pitch=float(effective_view_state.get("pitch", 0)),
        bearing=float(effective_view_state.get("bearing", 0)),
    )
    map_style, map_provider = map_basemap_configuration(basemap)
    deck = pdk.Deck(
        layers=[*map_basemap_layers(basemap), layer],
        initial_view_state=view_state,
        tooltip={"html": "{tooltip}"},
        map_style=map_style,
        map_provider=map_provider,
    )

    if not selectable:
        st.pydeck_chart(deck)
        return None

    try:
        event = st.pydeck_chart(
            deck,
            key=selection_key,
            on_select="rerun",
            selection_mode=selection_mode,
            width="stretch",
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

