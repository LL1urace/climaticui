"""
Модуль утилит для загрузки и обработки данных.
Содержит функции для загрузки CSV файлов с кэшированием.
"""

import pandas as pd
import streamlit as st
from pathlib import Path


def get_data_path() -> Path:
    """
    Возвращает абсолютный путь к папке data.
    Использует относительные пути относительно корня проекта.
    """
    # Получаем путь к текущему файлу
    current_file = Path(__file__).resolve()
    # Поднимаемся на уровень вверх (из utils/ в корень проекта)
    project_root = current_file.parent.parent
    return project_root / "data"


@st.cache_data
def load_stations() -> pd.DataFrame:
    """
    Загружает данные о метеостанциях из CSV файла.
    Кэширует результат для ускорения работы приложения.
    
    Returns:
        pd.DataFrame: DataFrame с данными о станциях или пустой DataFrame при ошибке.
        
    Columns:
        - station_id: идентификатор станции
        - name: название станции
        - latitude: широта
        - longitude: долгота
        - region: регион
        - elevation_m: высота над уровнем моря (м)
    """
    try:
        data_path = get_data_path() / "stations_coordinates.csv"
        
        if not data_path.exists():
            st.error(f"Файл не найден: {data_path}")
            return pd.DataFrame()
        
        df = pd.read_csv(data_path)
        
        # Валидация обязательных колонок
        required_columns = ['station_id', 'name', 'latitude', 'longitude', 'region', 'elevation_m']
        missing_columns = [col for col in required_columns if col not in df.columns]
        
        if missing_columns:
            st.error(f"Отсутствуют обязательные колонки: {missing_columns}")
            return pd.DataFrame()
        
        return df
    
    except pd.errors.EmptyDataError:
        st.error("Файл данных пуст или поврежден")
        return pd.DataFrame()
    except Exception as e:
        st.error(f"Ошибка загрузки станций: {e}")
        return pd.DataFrame()


@st.cache_data
def load_climate_data() -> pd.DataFrame:
    """
    Загружает климатические данные из CSV файла.
    Кэширует результат для ускорения работы приложения.
    
    Returns:
        pd.DataFrame: DataFrame с климатическими данными или пустой DataFrame при ошибке.
        
    Columns:
        - date: дата наблюдения
        - station_id: идентификатор станции
        - temperature_c: температура (°C)
        - humidity_pct: влажность (%)
        - pressure_hpa: давление (гПа)
        - wind_speed_ms: скорость ветра (м/с)
        - precipitation_mm: осадки (мм)
    """
    try:
        data_path = get_data_path() / "climate_data_sample.csv"
        
        if not data_path.exists():
            st.error(f"Файл не найден: {data_path}")
            return pd.DataFrame()
        
        df = pd.read_csv(data_path)
        
        # Валидация обязательных колонок
        required_columns = ['date', 'station_id', 'temperature_c', 'humidity_pct', 
                           'pressure_hpa', 'wind_speed_ms', 'precipitation_mm']
        missing_columns = [col for col in required_columns if col not in df.columns]
        
        if missing_columns:
            st.error(f"Отсутствуют обязательные колонки: {missing_columns}")
            return pd.DataFrame()
        
        # Преобразуем дату в datetime формат
        df['date'] = pd.to_datetime(df['date'])
        
        return df
    
    except pd.errors.EmptyDataError:
        st.error("Файл данных пуст или поврежден")
        return pd.DataFrame()
    except Exception as e:
        st.error(f"Ошибка загрузки климатических данных: {e}")
        return pd.DataFrame()


def get_available_metrics() -> list:
    """
    Возвращает список доступных метрик для анализа.
    
    Returns:
        list: Список кортежей (код метрики, отображаемое имя)
    """
    return [
        ('temperature_c', 'Температура (°C)'),
        ('humidity_pct', 'Влажность (%)'),
        ('pressure_hpa', 'Давление (гПа)'),
        ('wind_speed_ms', 'Скорость ветра (м/с)'),
        ('precipitation_mm', 'Осадки (мм)')
    ]


def get_station_name(stations_df: pd.DataFrame, station_id: str) -> str:
    """
    Возвращает название станции по её идентификатору.
    
    Args:
        stations_df: DataFrame с данными о станциях
        station_id: идентификатор станции
        
    Returns:
        str: Название станции или station_id если не найдена
    """
    if stations_df.empty:
        return station_id
    
    result = stations_df[stations_df['station_id'] == station_id]
    if result.empty:
        return station_id
    return result.iloc[0]['name']
