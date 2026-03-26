"""
Analytics - Аналитика и визуализация временных рядов
Графики изменения метрик, сравнение периодов, корреляционный анализ
"""

import streamlit as st
import sys
from pathlib import Path

# set_page_config должен быть ПЕРВЫМ вызовом Streamlit!
st.set_page_config(
    page_title="Аналитика - ClimaticUI",
    page_icon="📈",
    layout="wide"
)

# Добавляем корень проекта в sys.path для корректного импорта
project_root = Path(__file__).parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

import plotly.graph_objects as go
import plotly.express as px
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


def create_time_series_chart(
    climate_df: pd.DataFrame,
    stations_df: pd.DataFrame,
    selected_metrics: list,
    selected_stations: list
) -> go.Figure:
    """
    Создает график временных рядов для выбранных метрик и станций.
    
    Args:
        climate_df: DataFrame с климатическими данными
        stations_df: DataFrame с данными о станциях
        selected_metrics: Список выбранных метрик
        selected_stations: Список выбранных станций
        
    Returns:
        go.Figure: Plotly фигура с графиком
    """
    # Фильтрация данных
    filtered_df = climate_df[climate_df['station_id'].isin(selected_stations)].copy()
    
    # Словарь с названиями метрик
    metric_names = {
        'temperature_c': 'Температура (°C)',
        'humidity_pct': 'Влажность (%)',
        'pressure_hpa': 'Давление (гПа)',
        'wind_speed_ms': 'Ветер (м/с)',
        'precipitation_mm': 'Осадки (мм)'
    }
    
    # Цветовая палитра
    colors = px.colors.qualitative.Set1
    
    fig = go.Figure()
    
    # Добавляем линии для каждой станции
    for idx, station_id in enumerate(selected_stations):
        station_name = stations_df[
            stations_df['station_id'] == station_id
        ]['name'].iloc[0] if not stations_df.empty else station_id
        
        for metric_idx, metric in enumerate(selected_metrics):
            metric_data = filtered_df[filtered_df['station_id'] == station_id].sort_values('date')
            
            if metric_data.empty:
                continue
            
            # Формируем имя серии для легенды
            series_name = f"{station_name} - {metric_names.get(metric, metric)}"
            
            fig.add_trace(go.Scatter(
                x=metric_data['date'],
                y=metric_data[metric],
                name=series_name,
                line=dict(color=colors[metric_idx % len(colors)], width=2),
                mode='lines+markers',
                marker=dict(size=6),
                hovertemplate=(
                    f"<b>{station_name}</b><br>"
                    f"Дата: %{{x|%d.%m.%Y}}<br>"
                    f"{metric_names.get(metric, metric)}: %{{y:.2f}}<br>"
                    f"<extra></extra>"
                )
            ))
    
    # Настройка макета
    fig.update_layout(
        title="Динамика климатических показателей",
        xaxis_title="Дата",
        yaxis_title="Значение",
        hovermode='x unified',
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1
        ),
        showlegend=True
    )
    
    # Настройка осей
    fig.update_xaxes(
        tickformat="%d.%m.%Y",
        tickangle=45
    )
    
    return fig


def create_correlation_matrix(climate_df: pd.DataFrame) -> go.Figure:
    """
    Создает матрицу корреляций между метриками.
    
    Args:
        climate_df: DataFrame с климатическими данными
        
    Returns:
        go.Figure: Plotly фигура с тепловой картой корреляций
    """
    # Выбираем числовые колонки для корреляции
    numeric_cols = ['temperature_c', 'humidity_pct', 'pressure_hpa', 
                   'wind_speed_ms', 'precipitation_mm']
    
    # Расчет корреляционной матрицы
    corr_matrix = climate_df[numeric_cols].corr()
    
    # Названия метрик на русском
    metric_names_ru = {
        'temperature_c': 'Температура',
        'humidity_pct': 'Влажность',
        'pressure_hpa': 'Давление',
        'wind_speed_ms': 'Ветер',
        'precipitation_mm': 'Осадки'
    }
    
    # Переименовываем оси
    corr_matrix.index = [metric_names_ru.get(col, col) for col in corr_matrix.index]
    corr_matrix.columns = [metric_names_ru.get(col, col) for col in corr_matrix.columns]
    
    fig = go.Figure(data=go.Heatmap(
        z=corr_matrix.values,
        x=corr_matrix.columns,
        y=corr_matrix.index,
        colorscale='RdBu',
        zmid=0,
        text=corr_matrix.values.round(2),
        texttemplate="%{text}",
        textfont={"size": 12},
        hovertemplate="%{x} и %{y}: %{z:.3f}<extra></extra>"
    ))
    
    fig.update_layout(
        title="Матрица корреляций между показателями",
        xaxis_title="",
        yaxis_title=""
    )
    
    return fig


def create_comparison_chart(
    climate_df: pd.DataFrame,
    stations_df: pd.DataFrame,
    metric: str,
    station_id: str,
    period1_dates: tuple,
    period2_dates: tuple
) -> go.Figure:
    """
    Создает график сравнения двух периодов.
    
    Args:
        climate_df: DataFrame с климатическими данными
        stations_df: DataFrame с данными о станциях
        metric: Метрика для сравнения
        station_id: ID станции
        period1_dates: Кортеж (start_date, end_date) для периода 1
        period2_dates: Кортеж (start_date, end_date) для периода 2
        
    Returns:
        go.Figure: Plotly фигура с графиком сравнения
    """
    station_name = stations_df[
        stations_df['station_id'] == station_id
    ]['name'].iloc[0] if not stations_df.empty else station_id
    
    metric_names = {
        'temperature_c': 'Температура (°C)',
        'humidity_pct': 'Влажность (%)',
        'pressure_hpa': 'Давление (гПа)',
        'wind_speed_ms': 'Ветер (м/с)',
        'precipitation_mm': 'Осадки (мм)'
    }
    
    # Фильтрация данных по периодам
    period1_data = climate_df[
        (climate_df['station_id'] == station_id) &
        (climate_df['date'] >= period1_dates[0]) &
        (climate_df['date'] <= period1_dates[1])
    ].sort_values('date')
    
    period2_data = climate_df[
        (climate_df['station_id'] == station_id) &
        (climate_df['date'] >= period2_dates[0]) &
        (climate_df['date'] <= period2_dates[1])
    ].sort_values('date')
    
    fig = go.Figure()
    
    # Период 1
    fig.add_trace(go.Scatter(
        x=period1_data['date'],
        y=period1_data[metric],
        name=f"Период 1 ({period1_dates[0].strftime('%d.%m')} - {period1_dates[1].strftime('%d.%m')})",
        line=dict(color='blue', width=2),
        mode='lines+markers'
    ))
    
    # Период 2
    fig.add_trace(go.Scatter(
        x=period2_data['date'],
        y=period2_data[metric],
        name=f"Период 2 ({period2_dates[0].strftime('%d.%m')} - {period2_dates[1].strftime('%d.%m')})",
        line=dict(color='red', width=2, dash='dash'),
        mode='lines+markers'
    ))
    
    fig.update_layout(
        title=f"Сравнение периодов: {station_name} - {metric_names.get(metric, metric)}",
        xaxis_title="Дата",
        yaxis_title=metric_names.get(metric, metric),
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


def main():
    """
    Основная функция страницы Analytics.
    """
    st.title("📈 Аналитика")
    st.markdown("Визуализация временных рядов и сравнение периодов")
    st.markdown("---")
    
    # Загрузка данных
    stations_df = load_stations()
    climate_df = load_climate_data()
    
    # Проверка наличия данных
    if stations_df.empty or climate_df.empty:
        st.error("⚠️ Данные не загружены. Проверьте файлы в папке /data")
        return
    
    # Вкладки для разных типов анализа
    tab1, tab2 = st.tabs(["📊 Временные ряды", "🔗 Корреляции"])
    
    with tab1:
        # Боковая панель с фильтрами
        with st.sidebar:
            st.subheader("🎛️ Фильтры")
            
            # Выбор станций
            all_stations = stations_df['station_id'].tolist()
            selected_stations = st.multiselect(
                "Станции:",
                options=all_stations,
                default=all_stations[:3],  # Первые 3 по умолчанию
                format_func=lambda x: stations_df[
                    stations_df['station_id'] == x
                ]['name'].iloc[0] if not stations_df.empty else x
            )
            
            # Выбор метрик
            metrics = [m[0] for m in get_available_metrics()]
            selected_metrics = st.multiselect(
                "Метрики:",
                options=metrics,
                default=['temperature_c']
            )
        
        if not selected_stations or not selected_metrics:
            st.warning("Выберите хотя бы одну станцию и одну метрику")
            return
        
        # Отображение графика
        fig = create_time_series_chart(
            climate_df, stations_df,
            selected_metrics, selected_stations
        )
        st.plotly_chart(fig, use_container_width=True)
        
        # Статистика по выбранным данным
        st.subheader("📋 Статистика")
        
        filtered_df = climate_df[climate_df['station_id'].isin(selected_stations)]
        
        stats_data = []
        for station_id in selected_stations:
            station_data = filtered_df[filtered_df['station_id'] == station_id]
            station_name = stations_df[
                stations_df['station_id'] == station_id
            ]['name'].iloc[0]
            
            for metric in selected_metrics:
                stats_data.append({
                    'Станция': station_name,
                    'Метрика': metric,
                    'Среднее': station_data[metric].mean(),
                    'Мин': station_data[metric].min(),
                    'Макс': station_data[metric].max(),
                    'Стд. отклонение': station_data[metric].std()
                })
        
        stats_df = pd.DataFrame(stats_data)
        st.dataframe(stats_df.round(2), use_container_width=True)
    
    with tab2:
        # Матрица корреляций
        fig_corr = create_correlation_matrix(climate_df)
        st.plotly_chart(fig_corr, use_container_width=True)
        
        st.info("""
        **Интерпретация корреляций:**
        - Значения близкие к 1 — сильная положительная корреляция
        - Значения близкие к -1 — сильная отрицательная корреляция
        - Значения близкие к 0 — корреляция отсутствует
        """)


if __name__ == "__main__":
    main()
