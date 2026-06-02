# Источники локальных подложек карты

## Спутниковая обзорная подложка

- Исходный файл: `blue_marble_satellite.png`
- Подложка приложения: `../../static/maps/blue_marble_satellite_mercator.jpg`
- Источник: NASA Scientific Visualization Studio, Blue Marble
- Страница проекта: https://svs.gsfc.nasa.gov/2915/
- Исходный файл: https://svs.gsfc.nasa.gov/vis/a000000/a002900/a002915/bluemarble-2048.png

## Рельефная обзорная подложка

- Исходный архив: `NE1_50M_SR.zip`
- Подложка приложения: `../../static/maps/natural_earth_relief_mercator.jpg`
- Источник: Natural Earth I with Shaded Relief
- Страница проекта: https://www.naturalearthdata.com/downloads/50m-raster-data/50m-natural-earth-1/
- Назначение: автономная обзорная карта рельефа без загрузки сетевых тайлов

Подложки приложения преобразованы в проекцию Web Mercator с помощью
`scripts/build_offline_basemaps.py`, чтобы координаты станций совпадали с
позицией точек на стандартных онлайн-картах.

Локальные подложки предназначены для обзорного режима. Для подробного
масштабирования в приложении сохранены отдельные онлайн-подложки Esri.
