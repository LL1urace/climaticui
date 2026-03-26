"""
Forecast - Визуализация прогнозов
Отображение результатов прогнозирования с доверительными интервалами
"""

import streamlit as st
import sys
from pathlib import Path

# set_page_config должен быть ПЕРВЫМ вызовом Streamlit!
st.set_page_config(
    page_title="Прогноз - ClimaticUI",
    page_icon="🔮",
    layout="wide"
)

# Добавляем корень проекта в sys.path для корректного импорта
project_root = Path(__file__).parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

import plotly.graph_objects as go
import pandas as pd
import numpy as np
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


def generate_forecast_data(
    historical_df: pd.DataFrame,
    station_id: str,
    metric: str,
    forecast_days: int = 7
) -> pd.DataFrame:
    """
    Генерирует тестовые данные прогноза на основе исторических данных.
    В реальной системе здесь будет вызов ML-модели.
    
    Args:
        historical_df: DataFrame с историческими данными
        station_id: ID станции для прогноза
        metric: Метрика для прогнозирования
        forecast_days: Количество дней для прогноза
        
    Returns:
        pd.DataFrame: DataFrame с прогнозными данными
    """
    # Получаем исторические данные по станции
    station_data = historical_df[
        historical_df['station_id'] == station_id
    ].sort_values('date').copy()
    
    if station_data.empty:
        return pd.DataFrame()
    
    # Получаем последние значения
    last_date = station_data['date'].max()
    last_value = station_data[metric].iloc[-1]
    
    # Расчет статистик для генерации прогноза
    mean_value = station_data[metric].mean()
    std_value = station_data[metric].std()
    
    # Генерация прогноза с использованием простого тренда
    forecast_dates = [last_date + pd.Timedelta(days=i) for i in
                      range(1, forecast_days + 1)]
    forecast_dates = pd.to_datetime(forecast_dates)
    
    # Простая модель: тренд + случайная компонента
    trend = (last_value - mean_value) * 0.1  # Слабый тренд к среднему
    forecast_values = []
    upper_bound = []
    lower_bound = []
    
    for i in range(forecast_days):
        # Значение с трендом и шумом
        value = last_value + trend * (i + 1) + np.random.normal(0, std_value * 0.3)
        forecast_values.append(value)
        
        # Доверительный интервал (увеличивается с удалением от текущей даты)
        confidence_width = std_value * np.sqrt(i + 1) * 1.96
        upper_bound.append(value + confidence_width)
        lower_bound.append(value - confidence_width)
    
    forecast_df = pd.DataFrame({
        'date': forecast_dates,
        'station_id': station_id,
        f'{metric}_forecast': forecast_values,
        f'{metric}_upper': upper_bound,
        f'{metric}_lower': lower_bound
    })
    
    return forecast_df


def create_forecast_chart(
    historical_df: pd.DataFrame,
    forecast_df: pd.DataFrame,
    metric: str,
    station_name: str
) -> go.Figure:
    """
    Создает график с историческими данными и прогнозом.
    
    Args:
        historical_df: DataFrame с историческими данными
        forecast_df: DataFrame с прогнозными данными
        metric: Метрика для отображения
        station_name: Название станции
        
    Returns:
        go.Figure: Plotly фигура с графиком
    """
    metric_names = {
        'temperature_c': 'Температура (°C)',
        'humidity_pct': 'Влажность (%)',
        'pressure_hpa': 'Давление (гПа)',
        'wind_speed_ms': 'Ветер (м/с)',
        'precipitation_mm': 'Осадки (мм)'
    }
    
    y_label = metric_names.get(metric, metric)
    
    fig = go.Figure()
    
    # Исторические данные
    fig.add_trace(go.Scatter(
        x=historical_df['date'],
        y=historical_df[metric],
        name='Исторические данные',
        line=dict(color='blue', width=2),
        mode='lines+markers',
        marker=dict(size=6)
    ))
    
    # Прогноз
    forecast_col = f'{metric}_forecast'
    fig.add_trace(go.Scatter(
        x=forecast_df['date'],
        y=forecast_df[forecast_col],
        name='Прогноз',
        line=dict(color='red', width=2, dash='dash'),
        mode='lines+markers',
        marker=dict(size=6)
    ))
    
    # Доверительный интервал
    fig.add_trace(go.Scatter(
        x=pd.concat([forecast_df['date'], forecast_df['date'][::-1]]),
        y=pd.concat([forecast_df[f'{metric}_upper'], forecast_df[f'{metric}_lower'][::-1]]),
        fill='toself',
        fillcolor='rgba(255, 0, 0, 0.2)',
        line=dict(color='rgba(255, 0, 0, 0)'),
        hoverinfo='skip',
        name='Доверительный интервал (95%)'
    ))
    
    # Вертикальная линия разделения
    last_historical_date = historical_df['date'].max()
    fig.add_vline(
        x=last_historical_date.timestamp(),  # ✅ исправлено
        line_dash="dot",
        annotation_text="Начало прогноза",
        annotation_position="top",
        line_color="gray"
    )
    
    fig.update_layout(
        title=f"Прогноз: {station_name} - {y_label}",
        xaxis_title="Дата",
        yaxis_title=y_label,
        hovermode='x unified',
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1
        )
    )
    
    fig.update_xaxes(tickformat="%d.%m.%Y", tickangle=45)
    
    return fig


def calculate_forecast_accuracy(forecast_df: pd.DataFrame, metric: str) -> dict:
    """
    Рассчитывает метрики качества прогноза (для демонстрации).
    
    Args:
        forecast_df: DataFrame с прогнозными данными
        metric: Метрика прогноза
        
    Returns:
        dict: Словарь с метриками качества
    """
    # В реальной системе здесь будет сравнение с фактическими данными
    # Для демонстрации возвращаем тестовые значения
    
    return {
        'MAE': np.random.uniform(0.5, 2.0),
        'RMSE': np.random.uniform(0.8, 3.0),
        'MAPE': np.random.uniform(5, 15),
        'R²': np.random.uniform(0.75, 0.95)
    }


def main():
    """
    Основная функция страницы Forecast.
    """
    st.title("🔮 Прогноз")
    st.markdown("Визуализация результатов прогнозирования климатических показателей")
    st.markdown("---")
    
    # Загрузка данных
    stations_df = load_stations()
    climate_df = load_climate_data()
    
    # Проверка наличия данных
    if stations_df.empty or climate_df.empty:
        st.error("⚠️ Данные не загружены. Проверьте файлы в папке /data")
        return
    
    # Боковая панель с настройками
    with st.sidebar:
        st.subheader("🎛️ Параметры прогноза")
        
        # Выбор станции
        station_id = st.selectbox(
            "Станция:",
            options=stations_df['station_id'].tolist(),
            format_func=lambda x: stations_df[
                stations_df['station_id'] == x
            ]['name'].iloc[0]
        )
        
        # Выбор метрики
        metric = st.selectbox(
            "Метрика:",
            options=['temperature_c', 'humidity_pct', 'pressure_hpa', 
                    'wind_speed_ms', 'precipitation_mm'],
            format_func=lambda x: {
                'temperature_c': 'Температура (°C)',
                'humidity_pct': 'Влажность (%)',
                'pressure_hpa': 'Давление (гПа)',
                'wind_speed_ms': 'Ветер (м/с)',
                'precipitation_mm': 'Осадки (мм)'
            }.get(x, x)
        )
        
        # Горизонт прогноза
        forecast_days = st.slider(
            "Горизонт прогноза (дней):",
            min_value=1,
            max_value=14,
            value=7
        )
        
        # Кнопка генерации прогноза
        generate_btn = st.button("🔄 Сгенерировать прогноз", type="primary")
    
    # Получение названия станции
    station_name = stations_df[
        stations_df['station_id'] == station_id
    ]['name'].iloc[0]
    
    # Исторические данные
    historical_data = climate_df[
        climate_df['station_id'] == station_id
    ].sort_values('date')
    
    if historical_data.empty:
        st.warning("Нет данных для выбранной станции")
        return
    
    # Генерация прогноза
    with st.spinner("Генерация прогноза..."):
        forecast_data = generate_forecast_data(
            historical_data, station_id, metric, forecast_days
        )
    
    if forecast_data.empty:
        st.error("Ошибка генерации прогноза")
        return
    
    # Отображение графика
    fig = create_forecast_chart(
        historical_data, forecast_data, metric, station_name
    )
    st.plotly_chart(fig, use_container_width=True)
    
    # Метрики качества прогноза
    st.subheader("📊 Оценка качества прогноза")
    
    accuracy_metrics = calculate_forecast_accuracy(forecast_data, metric)
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("MAE", f"{accuracy_metrics['MAE']:.2f}")
    
    with col2:
        st.metric("RMSE", f"{accuracy_metrics['RMSE']:.2f}")
    
    with col3:
        st.metric("MAPE", f"{accuracy_metrics['MAPE']:.1f}%")
    
    with col4:
        st.metric("R²", f"{accuracy_metrics['R²']:.2f}")
    
    # Дисклеймер
    st.info("""
    ⚠️ **Важно:** Данный прогноз является демонстрационным.
    
    В production-версии здесь будет использоваться реальная ML-модель,
    обученная на исторических климатических данных.
    
    **Точность прогноза** зависит от:
    - Количества и качества исторических данных
    - Выбранной модели прогнозирования
    - Горизонта прогноза (краткосрочные точнее долгосрочных)
    - Характера прогнозируемой метрики
    """)
    
    # Таблица с прогнозными значениями
    st.subheader("📋 Прогнозные значения")
    
    display_df = forecast_data.copy()
    display_df['date'] = display_df['date'].dt.strftime('%d.%m.%Y')
    display_df = display_df.rename(columns={
        'date': 'Дата',
        f'{metric}_forecast': 'Прогноз',
        f'{metric}_upper': 'Верхняя граница (95%)',
        f'{metric}_lower': 'Нижняя граница (95%)'
    })
    
    st.dataframe(
        display_df[['Дата', 'Прогноз', 'Нижняя граница (95%)', 'Верхняя граница (95%)']],
        use_container_width=True,
        hide_index=True
    )


if __name__ == "__main__":
    main()
