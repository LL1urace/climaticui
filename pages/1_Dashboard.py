"""
Dashboard - Главная панель мониторинга
Отображение ключевых метрик и сводных данных

Lifecycle защищённой страницы:
1. set_page_config
2. init session_state
3. если НЕ залогинен → redirect в login
4. загрузить приложение
"""

import streamlit as st
import sys
from pathlib import Path

# set_page_config должен быть ПЕРВЫМ вызовом Streamlit!
st.set_page_config(
    page_title="Dashboard - ClimaticUI",
    page_icon="📊",
    layout="wide"
)

# Добавляем корень проекта в sys.path
project_root = Path(__file__).parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

# Импорты
import pandas as pd
from utils.data_loader import load_stations, load_climate_data, get_available_metrics
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


def calculate_kpis(climate_df: pd.DataFrame) -> dict:
    """
    Вычисляет ключевые показатели (KPI) для дашборда.
    
    Args:
        climate_df: DataFrame с климатическими данными
        
    Returns:
        dict: Словарь с рассчитанными KPI
    """
    kpis = {
        'avg_temperature': climate_df['temperature_c'].mean(),
        'max_temperature': climate_df['temperature_c'].max(),
        'min_temperature': climate_df['temperature_c'].min(),
        'avg_humidity': climate_df['humidity_pct'].mean(),
        'avg_pressure': climate_df['pressure_hpa'].mean(),
        'avg_wind_speed': climate_df['wind_speed_ms'].mean(),
        'total_precipitation': climate_df['precipitation_mm'].sum(),
        'stations_count': climate_df['station_id'].nunique(),
        'records_count': len(climate_df)
    }
    return kpis


def render_kpi_cards(kpis: dict):
    """
    Отображает KPI в виде карточек метрик.
    
    Args:
        kpis: Словарь с рассчитанными показателями
    """
    # Первая строка KPI
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric(
            label="🌡️ Средняя температура",
            value=f"{kpis['avg_temperature']:.1f}°C",
            delta=f"{kpis['max_temperature'] - kpis['avg_temperature']:.1f}°C (макс)"
        )
    
    with col2:
        st.metric(
            label="💧 Средняя влажность",
            value=f"{kpis['avg_humidity']:.1f}%",
            delta=None
        )
    
    with col3:
        st.metric(
            label="📊 Среднее давление",
            value=f"{kpis['avg_pressure']:.1f} гПа",
            delta=None
        )
    
    with col4:
        st.metric(
            label="💨 Средний ветер",
            value=f"{kpis['avg_wind_speed']:.1f} м/с",
            delta=None
        )
    
    # Вторая строка KPI
    col5, col6, col7, col8 = st.columns(4)
    
    with col5:
        st.metric(
            label="🌡️ Мин. температура",
            value=f"{kpis['min_temperature']:.1f}°C",
            delta=f"{kpis['max_temperature'] - kpis['min_temperature']:.1f}°C диапазон"
        )
    
    with col6:
        st.metric(
            label="🌡️ Макс. температура",
            value=f"{kpis['max_temperature']:.1f}°C",
            delta=None
        )
    
    with col7:
        st.metric(
            label="🌊 Осадки (сумма)",
            value=f"{kpis['total_precipitation']:.1f} мм",
            delta=None
        )
    
    with col8:
        st.metric(
            label="📍 Станций",
            value=kpis['stations_count'],
            delta=f"{kpis['records_count']} записей"
        )


def render_data_preview(climate_df: pd.DataFrame, stations_df: pd.DataFrame):
    """
    Отображает таблицу с предпросмотром данных.
    
    Args:
        climate_df: DataFrame с климатическими данными
        stations_df: DataFrame с данными о станциях
    """
    st.subheader("📋 Предпросмотр данных")
    
    # Объединяем данные для отображения
    merged_df = climate_df.merge(
        stations_df[['station_id', 'name', 'region']],
        on='station_id',
        how='left'
    )
    
    # Переименовываем колонки для отображения
    display_df = merged_df.copy()
    display_df = display_df.rename(columns={
        'date': 'Дата',
        'station_id': 'ID станции',
        'name': 'Станция',
        'region': 'Регион',
        'temperature_c': 'Температура (°C)',
        'humidity_pct': 'Влажность (%)',
        'pressure_hpa': 'Давление (гПа)',
        'wind_speed_ms': 'Ветер (м/с)',
        'precipitation_mm': 'Осадки (мм)'
    })
    
    # Форматируем дату
    display_df['Дата'] = display_df['Дата'].dt.strftime('%d.%m.%Y')
    
    # Отображаем таблицу
    st.dataframe(
        display_df[['Дата', 'Станция', 'Регион', 'Температура (°C)', 
                   'Влажность (%)', 'Давление (гПа)', 'Ветер (м/с)', 'Осадки (мм)']],
        use_container_width=True,
        hide_index=True
    )


def main():
    """
    Основная функция страницы Dashboard.
    """
    st.title("📊 Dashboard")
    st.markdown("Сводные показатели и ключевые метрики системы")
    st.markdown("---")
    
    # Загрузка данных
    stations_df = load_stations()
    climate_df = load_climate_data()
    
    # Проверка наличия данных
    if stations_df.empty or climate_df.empty:
        st.error("⚠️ Данные не загружены. Проверьте файлы в папке /data")
        return
    
    # Расчет KPI
    kpis = calculate_kpis(climate_df)
    
    # Отображение KPI карточек
    render_kpi_cards(kpis)
    
    st.markdown("---")
    
    # Предпросмотр данных
    render_data_preview(climate_df, stations_df)
    
    # Статус системы
    st.markdown("---")
    st.subheader("🖥️ Статус системы")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.success("✅ Данные загружены")
        st.info(f"📁 Станций: {len(stations_df)}")
    
    with col2:
        st.success("✅ API готов к работе")
        st.info(f"📊 Записей: {kpis['records_count']}")


if __name__ == "__main__":
    main()
