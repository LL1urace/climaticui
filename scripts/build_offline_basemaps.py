"""Подготавливает локальные Web Mercator-подложки для карты метеостанций."""

from __future__ import annotations

from math import atan, degrees, pi, sinh
from pathlib import Path
from zipfile import ZipFile

import numpy as np
from PIL import Image


ROOT_DIR = Path(__file__).resolve().parents[1]
MAP_ASSETS_DIR = ROOT_DIR / "app" / "assets" / "maps"
SATELLITE_SOURCE = MAP_ASSETS_DIR / "blue_marble_satellite.png"
RELIEF_ARCHIVE = MAP_ASSETS_DIR / "NE1_50M_SR.zip"
RELIEF_ARCHIVE_IMAGE = "NE1_50M_SR/NE1_50M_SR.tif"
SATELLITE_OUTPUT = MAP_ASSETS_DIR / "blue_marble_satellite_mercator.jpg"
RELIEF_OUTPUT = MAP_ASSETS_DIR / "natural_earth_relief_mercator.jpg"
OUTPUT_SIZE = 2048


def _mercator_source_rows(source_height: int, output_height: int) -> np.ndarray:
    """Рассчитывает строки эквидистантного исходника для Web Mercator-растра.

    Args:
        source_height: Высота исходного изображения в пикселях.
        output_height: Высота результирующего изображения в пикселях.

    Returns:
        Массив дробных индексов строк исходного изображения.
    """

    target_rows = np.linspace(0.0, 1.0, output_height, dtype=np.float64)
    latitudes = np.array(
        [degrees(atan(sinh(pi * (1.0 - 2.0 * row)))) for row in target_rows],
        dtype=np.float64,
    )
    return (90.0 - latitudes) / 180.0 * (source_height - 1)


def _reproject_to_web_mercator(source: Image.Image, output_size: int) -> Image.Image:
    """Преобразует эквидистантный мировой raster в проекцию Web Mercator.

    Args:
        source: Исходная карта мира в географической проекции EPSG:4326.
        output_size: Размер стороны квадратного результата в пикселях.

    Returns:
        Перепроецированное RGB-изображение карты мира.
    """

    source = source.convert("RGB")
    resized_height = round(source.height * output_size / source.width)
    resized = source.resize((output_size, resized_height), Image.Resampling.LANCZOS)
    source_pixels = np.asarray(resized, dtype=np.float32)
    source_rows = _mercator_source_rows(resized_height, output_size)
    lower_rows = np.floor(source_rows).astype(np.int32)
    upper_rows = np.minimum(lower_rows + 1, resized_height - 1)
    fractions = (source_rows - lower_rows).astype(np.float32)[:, np.newaxis, np.newaxis]
    projected = source_pixels[lower_rows] * (1.0 - fractions) + source_pixels[upper_rows] * fractions
    return Image.fromarray(np.clip(projected, 0, 255).astype(np.uint8), mode="RGB")


def _replace_relief_background(source: Image.Image) -> Image.Image:
    """Заменяет белый фон raster-рельефа на тёмно-синий цвет океана.

    Args:
        source: Перепроецированное изображение Natural Earth.

    Returns:
        Изображение рельефа с тёмным океаном.
    """

    pixels = np.asarray(source.convert("RGB")).copy()
    ocean_mask = np.min(pixels, axis=2) > 245
    pixels[ocean_mask] = [7, 17, 31]
    return Image.fromarray(pixels, mode="RGB")


def _save_web_mercator(source: Image.Image, output: Path, dark_ocean: bool = False) -> None:
    """Сохраняет Web Mercator-версию raster-подложки в JPEG.

    Args:
        source: Исходное изображение подложки.
        output: Путь результирующего JPEG-файла.
        dark_ocean: Заменяет белый фон рельефа на тёмно-синий океан.

    Returns:
        None.
    """

    projected = _reproject_to_web_mercator(source, OUTPUT_SIZE)
    if dark_ocean:
        projected = _replace_relief_background(projected)
    projected.save(output, quality=88, optimize=True, progressive=True)


def build_offline_basemaps() -> None:
    """Создаёт локальные спутниковую и рельефную подложки карты.

    Returns:
        None.

    Raises:
        FileNotFoundError: Если исходный PNG или архив Natural Earth отсутствует.
    """

    _save_web_mercator(Image.open(SATELLITE_SOURCE), SATELLITE_OUTPUT)
    with ZipFile(RELIEF_ARCHIVE) as archive:
        with archive.open(RELIEF_ARCHIVE_IMAGE) as relief_file:
            _save_web_mercator(Image.open(relief_file), RELIEF_OUTPUT, dark_ocean=True)


if __name__ == "__main__":
    build_offline_basemaps()
