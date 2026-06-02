from __future__ import annotations

import json
from urllib.parse import unquote

from app.components.maps import (
    CARTO_DARK_MATTER_STYLE,
    ESRI_WORLD_IMAGERY_TILES,
    LOCAL_MAP_ASSETS_URL,
    _station_color,
    classification_gradient_css,
    map_basemap_configuration,
    map_basemap_layers,
    map_view_for_points,
    station_classification_color,
    station_map_palette,
)


def test_station_map_palette_converts_hex_colors_to_rgba() -> None:
    """Проверяет преобразование цветов интерфейса в палитру PyDeck.

    Returns:
        None.
    """

    palette = station_map_palette("#f59e0b", "#4a95ff", "#062245")

    assert palette["selected"] == [245, 158, 11, 235]
    assert palette["real"] == [74, 149, 255, 165]
    assert palette["synthetic"] == [6, 34, 69, 170]


def test_station_color_prefers_selected_color_over_data_type() -> None:
    """Проверяет приоритет цвета выбранной станции над типом данных.

    Returns:
        None.
    """

    palette = station_map_palette("#111111", "#222222", "#333333")

    assert _station_color({"_selected": True, "data_quality": "real_monthly"}, palette) == [17, 17, 17, 235]
    assert _station_color({"data_quality": "real_monthly"}, palette) == [34, 34, 34, 165]
    assert _station_color({"data_quality": "sample_generated"}, palette) == [51, 51, 51, 170]


def test_station_classification_color_uses_gradient_and_neutral_fallback() -> None:
    """Проверяет градиентную раскраску климатического параметра."""

    assert station_classification_color(0, 0, 10) == [13, 100, 216, 210]
    assert station_classification_color(5, 0, 10) == [118, 228, 197, 210]
    assert station_classification_color(10, 0, 10) == [234, 88, 12, 210]
    assert station_classification_color(None, 0, 10) == [100, 116, 139, 145]


def test_station_classification_color_supports_alternative_gradient() -> None:
    """Проверяет выбор альтернативной палитры классификации."""

    assert station_classification_color(0, 0, 10, gradient_name="forest") == [5, 150, 105, 210]
    assert station_classification_color(10, 0, 10, gradient_name="forest") == [159, 18, 57, 210]
    assert classification_gradient_css("forest").startswith("rgb(5,150,105)")


def test_station_color_applies_gradient_to_selected_station_during_classification() -> None:
    """Проверяет градиентную раскраску всех станций, включая выбранные."""

    palette = station_map_palette("#f59e0b", "#222222", "#333333")
    classification = {
        "value_key": "classification_mean",
        "min_value": 0,
        "max_value": 10,
        "gradient_name": "forest",
    }

    assert _station_color({"classification_mean": 0}, palette, classification) == [5, 150, 105, 210]
    assert _station_color({"_selected": True, "classification_mean": 0}, palette, classification) == [5, 150, 105, 210]


def test_map_view_for_points_centers_single_station() -> None:
    """Проверяет центрирование карты на одной выбранной станции.

    Returns:
        None.
    """

    view = map_view_for_points([67.5], [64.0])

    assert view["latitude"] == 67.5
    assert view["longitude"] == 64.0
    assert view["zoom"] == 5.0


def test_map_view_for_points_fits_distant_stations() -> None:
    """Проверяет уменьшение масштаба для удалённых выбранных станций.

    Returns:
        None.
    """

    view = map_view_for_points([43.2, 71.6], [37.6, 128.9])

    assert view["latitude"] == 57.4
    assert view["longitude"] == 83.25
    assert 1.0 <= view["zoom"] < 2.0


def test_map_basemap_configuration_uses_dark_matter_by_default() -> None:
    """Проверяет выбор стандартной тёмной подложки CARTO Dark Matter.

    Returns:
        None.
    """

    style, provider = map_basemap_configuration(None)

    assert style == CARTO_DARK_MATTER_STYLE
    assert provider == "carto"


def test_map_basemap_configuration_builds_satellite_raster_style() -> None:
    """Проверяет конфигурацию спутниковой raster-подложки Esri.

    Returns:
        None.
    """

    style, provider = map_basemap_configuration("satellite")

    assert provider == "carto"
    assert style.startswith("data:application/json;charset=utf-8,")
    raster_style = json.loads(unquote(style.split(",", 1)[1]))
    assert raster_style["sources"]["basemap"]["tiles"] == [ESRI_WORLD_IMAGERY_TILES]


def test_map_basemap_configuration_builds_local_background_style() -> None:
    """Проверяет автономный фоновый стиль для локальных подложек.

    Returns:
        None.
    """

    for basemap in ("satellite_local", "topographic_local"):
        style, provider = map_basemap_configuration(basemap)

        assert provider == "carto"
        assert style.startswith("data:application/json;charset=utf-8,")
        background_style = json.loads(unquote(style.split(",", 1)[1]))
        assert background_style["sources"] == {}
        assert background_style["layers"][0]["type"] == "background"


def test_map_basemap_layers_uses_local_static_images() -> None:
    """Проверяет URL локальных изображений подложек.

    Returns:
        None.
    """

    for basemap in ("satellite_local", "topographic_local"):
        layers = map_basemap_layers(basemap)
        layer_json = layers[0].to_json()

        assert len(layers) == 1
        assert '"@@type": "BitmapLayer"' in layer_json
        assert f'"image": "{LOCAL_MAP_ASSETS_URL}/' in layer_json


def test_map_basemap_layers_returns_empty_list_for_online_style() -> None:
    """Проверяет отсутствие bitmap-слоя у сетевой подложки.

    Returns:
        None.
    """

    assert map_basemap_layers("satellite") == []
