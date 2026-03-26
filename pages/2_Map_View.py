"""
Map View - Интерактивная карта метеостанций
Визуализация станций на карте Евразии с цветовым кодированием
"""

import streamlit as st
import sys
from pathlib import Path

# set_page_config должен быть ПЕРВЫМ вызовом Streamlit!
st.set_page_config(
    page_title="Карта метеостанций - ClimaticUI",
    page_icon="🗺️",
    layout="wide"
)

# Добавляем корень проекта в sys.path для корректного импорта
project_root = Path(__file__).parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

import plotly.express as px
import pandas as pd
from utils.data_loader import load_stations, load_climate_data
from utils.auth_session import (
    init_session_state,
    check_and_restore_session,
    require_auth,
    render_navbar,
    load_css_styles
)

# 2. Инициализация session_state
init_session_state()

# 3. Восстановление сессии из cookies
check_and_restore_session()

# 5. Защита страницы - если не авторизован, редирект на login
require_auth()

# 4. Загрузка стилей и навигации
load_css_styles()
render_navbar()


def prepare_map_data(stations_df: pd.DataFrame, climate_df: pd.DataFrame) -> pd.DataFrame:
    """
    Подготавливает данные для отображения на карте.
    Объединяет данные станций с последними климатическими показателями.
    
    Args:
        stations_df: DataFrame с данными о станциях
        climate_df: DataFrame с климатическими данными
        
    Returns:
        pd.DataFrame: Объединенные данные для карты
    """
    # Получаем последние данные по каждой станции
    latest_data = climate_df.loc[
        climate_df.groupby('station_id')['date'].idxmax()
    ].copy()
    
    # Объединяем с данными о станциях
    map_df = stations_df.merge(
        latest_data[['station_id', 'temperature_c', 'humidity_pct', 'pressure_hpa']],
        on='station_id',
        how='left'
    )
    
    return map_df


def create_scatter_geo_map(map_df: pd.DataFrame, color_metric: str) -> px.scatter_geo:
    """
    Создает интерактивную карту с метеостанциями.
    
    Args:
        map_df: DataFrame с данными для карты
        color_metric: Метрика для цветового кодирования
        
    Returns:
        px.scatter_geo: Plotly фигура карты
    """
    # Настройка цветовой метрики
    color_labels = {
        'temperature_c': 'Температура (°C)',
        'humidity_pct': 'Влажность (%)',
        'pressure_hpa': 'Давление (гПа)'
    }
    
    # Создание карты
    fig = px.scatter_geo(
        map_df,
        lat='latitude',
        lon='longitude',
        color=color_metric,
        hover_name='name',
        hover_data={
            'latitude': False,
            'longitude': False,
            'region': True,
            'elevation_m': True,
            color_metric: f':.1f'
        },
        color_continuous_scale='RdYlBu_r' if color_metric == 'temperature_c' else 'Viridis',
        size_max=20,
        title='Расположение метеостанций Евразии',
        labels={color_metric: color_labels.get(color_metric, color_metric)}
    )
    
    # Настройка проекции карты
    fig.update_geos(
        projection_type="natural earth",
        center_lat=45,
        center_lon=70,
        resolution=50,
        showcountries=True,
        countrycolor="Black",
        showcoastlines=True,
        coastlinecolor="RebeccaPurple",
        showland=True,
        landcolor="LightGreen",
        showocean=True,
        oceancolor="LightBlue",
        lataxis_showgrid=True,
        lonaxis_showgrid=True,
    )
    
    # Настройка макета
    fig.update_layout(
        height=600,
        margin={"r": 0, "t": 50, "l": 0, "b": 0},
        geo=dict(
            scope="asia",
            showland=True,
            landcolor="rgb(230, 230, 230)",
            countrycolor="rgb(200, 200, 200)",
            coastlinecolor="rgb(150, 150, 150)",
        ),
    )
    
    return fig


def create_station_info_card(map_df: pd.DataFrame, selected_station: str) -> None:
    """
    Отображает карточку с информацией о выбранной станции.
    
    Args:
        map_df: DataFrame с данными для карты
        selected_station: ID выбранной станции
    """
    station_data = map_df[map_df['station_id'] == selected_station]
    
    if station_data.empty:
        st.warning("Станция не найдена")
        return
    
    station = station_data.iloc[0]
    
    st.subheader(f"📍 {station['name']}")
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("Температура", f"{station.get('temperature_c', 'N/A')}°C")
    
    with col2:
        st.metric("Влажность", f"{station.get('humidity_pct', 'N/A')}%")
    
    with col3:
        st.metric("Давление", f"{station.get('pressure_hpa', 'N/A')} гПа")
    
    with col4:
        st.metric("Регион", station['region'])
    
    st.caption(f"Высота над уровнем моря: {station['elevation_m']} м")


def main():
    """
    Основная функция страницы Map View.
    """
    st.title("🗺️ Карта метеостанций")
    st.markdown("Интерактивная карта с расположением и показателями метеостанций")
    st.markdown("---")
    
    # Загрузка данных
    stations_df = load_stations()
    climate_df = load_climate_data()
    
    # Проверка наличия данных
    if stations_df.empty or climate_df.empty:
        st.error("⚠️ Данные не загружены. Проверьте файлы в папке /data")
        return
    
    # Подготовка данных для карты
    map_df = prepare_map_data(stations_df, climate_df)
    
    # Боковая панель с фильтрами
    with st.sidebar:
        st.subheader("🎛️ Настройки карты")
        
        # Выбор метрики для цветового кодирования
        color_metric = st.selectbox(
            "Цветовая метрика:",
            options=['temperature_c', 'humidity_pct', 'pressure_hpa'],
            format_func=lambda x: {
                'temperature_c': 'Температура (°C)',
                'humidity_pct': 'Влажность (%)',
                'pressure_hpa': 'Давление (гПа)'
            }.get(x, x)
        )
        
        # Фильтр по региону
        regions = ['Все регионы'] + sorted(stations_df['region'].unique().tolist())
        selected_region = st.selectbox("Регион:", regions)
        
        # Применение фильтра
        if selected_region != 'Все регионы':
            map_df = map_df[map_df['region'] == selected_region]
    
    # Отображение карты
    fig = create_scatter_geo_map(map_df, color_metric)
    st.plotly_chart(fig, use_container_width=True)
    
    # Выбор станции для детальной информации
    st.markdown("---")
    st.subheader("📋 Информация о станции")
    
    station_options = map_df['station_id'].unique()
    selected_station = st.selectbox(
        "Выберите станцию:",
        options=station_options,
        format_func=lambda x: map_df[map_df['station_id'] == x].iloc[0]['name']
    )
    
    if selected_station:
        create_station_info_card(map_df, selected_station)


if __name__ == "__main__":
    main()
