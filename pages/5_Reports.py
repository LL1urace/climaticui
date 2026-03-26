"""
Reports - Генерация и экспорт отчётов
Создание сводных отчётов, экспорт данных и графиков
"""

import streamlit as st
import sys
from pathlib import Path

# set_page_config должен быть ПЕРВЫМ вызовом Streamlit!
st.set_page_config(
    page_title="Отчёты - ClimaticUI",
    page_icon="📑",
    layout="wide"
)

# Добавляем корень проекта в sys.path для корректного импорта
project_root = Path(__file__).parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

import pandas as pd
import plotly.graph_objects as go
from datetime import datetime
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


def generate_summary_report(
    stations_df: pd.DataFrame,
    climate_df: pd.DataFrame,
    selected_region: str = None
) -> dict:
    """
    Генерирует сводный отчёт по данным.
    
    Args:
        stations_df: DataFrame с данными о станциях
        climate_df: DataFrame с климатическими данными
        selected_region: Выбранный регион для фильтрации
        
    Returns:
        dict: Словарь с данными отчёта
    """
    # Фильтрация по региону
    if selected_region and selected_region != 'Все регионы':
        station_ids = stations_df[
            stations_df['region'] == selected_region
        ]['station_id'].tolist()
        climate_df = climate_df[climate_df['station_id'].isin(station_ids)]
        stations_df = stations_df[stations_df['station_id'].isin(station_ids)]
    
    # Расчет статистик
    report = {
        'generated_at': datetime.now().strftime('%d.%m.%Y %H:%M'),
        'period': {
            'start': climate_df['date'].min().strftime('%d.%m.%Y'),
            'end': climate_df['date'].max().strftime('%d.%m.%Y'),
            'days': (climate_df['date'].max() - climate_df['date'].min()).days + 1
        },
        'stations': {
            'total': len(stations_df),
            'regions': stations_df['region'].nunique() if not stations_df.empty else 0
        },
        'records': len(climate_df),
        'metrics': {
            'temperature': {
                'mean': climate_df['temperature_c'].mean(),
                'min': climate_df['temperature_c'].min(),
                'max': climate_df['temperature_c'].max(),
                'std': climate_df['temperature_c'].std()
            },
            'humidity': {
                'mean': climate_df['humidity_pct'].mean(),
                'min': climate_df['humidity_pct'].min(),
                'max': climate_df['humidity_pct'].max(),
                'std': climate_df['humidity_pct'].std()
            },
            'pressure': {
                'mean': climate_df['pressure_hpa'].mean(),
                'min': climate_df['pressure_hpa'].min(),
                'max': climate_df['pressure_hpa'].max(),
                'std': climate_df['pressure_hpa'].std()
            },
            'wind': {
                'mean': climate_df['wind_speed_ms'].mean(),
                'max': climate_df['wind_speed_ms'].max()
            },
            'precipitation': {
                'total': climate_df['precipitation_mm'].sum(),
                'days_with_precip': len(climate_df[climate_df['precipitation_mm'] > 0])
            }
        }
    }
    
    return report


def create_csv_export(climate_df: pd.DataFrame, stations_df: pd.DataFrame) -> pd.DataFrame:
    """
    Подготавливает данные для экспорта в CSV.
    
    Args:
        climate_df: DataFrame с климатическими данными
        stations_df: DataFrame с данными о станциях
        
    Returns:
        pd.DataFrame: Объединенные данные для экспорта
    """
    # Объединение данных
    export_df = climate_df.merge(
        stations_df[['station_id', 'name', 'region', 'elevation_m']],
        on='station_id',
        how='left'
    )
    
    # Переименование колонок
    export_df = export_df.rename(columns={
        'date': 'Дата',
        'station_id': 'ID_станции',
        'name': 'Название_станции',
        'region': 'Регион',
        'elevation_m': 'Высота_м',
        'temperature_c': 'Температура_C',
        'humidity_pct': 'Влажность_%',
        'pressure_hpa': 'Давление_гПа',
        'wind_speed_ms': 'Ветер_м/с',
        'precipitation_mm': 'Осадки_мм'
    })
    
    # Форматирование даты
    export_df['Дата'] = export_df['Дата'].dt.strftime('%Y-%m-%d')
    
    return export_df


def generate_report_text(report: dict) -> str:
    """
    Генерирует текстовую версию отчёта.
    
    Args:
        report: Словарь с данными отчёта
        
    Returns:
        str: Текстовая версия отчёта
    """
    text = f"""
ОТЧЁТ ПО КЛИМАТИЧЕСКИМ ДАННЫМ
=============================
Сгенерирован: {report['generated_at']}

ПЕРИОД АНАЛИЗА
--------------
{report['period']['start']} - {report['period']['end']} ({report['period']['days']} дн.)

ОБЩИЕ СВЕДЕНИЯ
--------------
Метеостанций: {report['stations']['total']}
Регионов: {report['stations']['regions']}
Всего записей: {report['records']}

ТЕМПЕРАТУРА
-----------
Средняя: {report['metrics']['temperature']['mean']:.2f}°C
Минимальная: {report['metrics']['temperature']['min']:.2f}°C
Максимальная: {report['metrics']['temperature']['max']:.2f}°C
Стд. отклонение: {report['metrics']['temperature']['std']:.2f}°C

ВЛАЖНОСТЬ
---------
Средняя: {report['metrics']['humidity']['mean']:.2f}%
Минимальная: {report['metrics']['humidity']['min']:.2f}%
Максимальная: {report['metrics']['humidity']['max']:.2f}%

ДАВЛЕНИЕ
--------
Среднее: {report['metrics']['pressure']['mean']:.2f} гПа
Минимальное: {report['metrics']['pressure']['min']:.2f} гПа
Максимальное: {report['metrics']['pressure']['max']:.2f} гПа

ВЕТЕР
-----
Средняя скорость: {report['metrics']['wind']['mean']:.2f} м/с
Максимальная скорость: {report['metrics']['wind']['max']:.2f} м/с

ОСАДКИ
------
Суммарно: {report['metrics']['precipitation']['total']:.2f} мм
Дней с осадками: {report['metrics']['precipitation']['days_with_precip']}

=============================
ClimaticUI v0.1.0
    """.strip()
    
    return text


def main():
    """
    Основная функция страницы Reports.
    """
    st.title("📑 Отчёты")
    st.markdown("Генерация и экспорт отчётов по климатическим данным")
    st.markdown("---")
    
    # Загрузка данных
    stations_df = load_stations()
    climate_df = load_climate_data()
    
    # Проверка наличия данных
    if stations_df.empty or climate_df.empty:
        st.error("⚠️ Данные не загружены. Проверьте файлы в папке /data")
        return
    
    # Боковая панель с настройками отчёта
    with st.sidebar:
        st.subheader("🎛️ Параметры отчёта")
        
        # Выбор региона
        regions = ['Все регионы'] + sorted(stations_df['region'].unique().tolist())
        selected_region = st.selectbox("Регион:", regions)
        
        # Выбор формата экспорта
        export_format = st.radio(
            "Формат экспорта:",
            options=['CSV', 'TXT'],
            help="Выберите формат для выгрузки данных"
        )
        
        # Кнопка генерации
        generate_btn = st.button("📄 Сгенерировать отчёт", type="primary")
    
    # Генерация отчёта
    report = generate_summary_report(stations_df, climate_df, selected_region)
    
    # Отображение сводной информации
    st.subheader("📊 Сводка отчёта")
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("Период", f"{report['period']['days']} дней")
    
    with col2:
        st.metric("Станций", report['stations']['total'])
    
    with col3:
        st.metric("Записей", report['records'])
    
    with col4:
        st.metric("Регионов", report['stations']['regions'])
    
    st.markdown("---")
    
    # Детальные метрики
    st.subheader("📈 Ключевые показатели")
    
    metrics_col1, metrics_col2 = st.columns(2)
    
    with metrics_col1:
        st.markdown("**🌡️ Температура**")
        st.write(f"Средняя: **{report['metrics']['temperature']['mean']:.2f}°C**")
        st.write(f"Диапазон: {report['metrics']['temperature']['min']:.2f}°C ... {report['metrics']['temperature']['max']:.2f}°C")
    
    with metrics_col2:
        st.markdown("**💧 Влажность**")
        st.write(f"Средняя: **{report['metrics']['humidity']['mean']:.2f}%**")
        st.write(f"Диапазон: {report['metrics']['humidity']['min']:.2f}% ... {report['metrics']['humidity']['max']:.2f}%")
    
    metrics_col3, metrics_col4 = st.columns(2)
    
    with metrics_col3:
        st.markdown("**📊 Давление**")
        st.write(f"Среднее: **{report['metrics']['pressure']['mean']:.2f} гПа**")
    
    with metrics_col4:
        st.markdown("**🌊 Осадки**")
        st.write(f"Суммарно: **{report['metrics']['precipitation']['total']:.2f} мм**")
        st.write(f"Дней с осадками: **{report['metrics']['precipitation']['days_with_precip']}**")
    
    st.markdown("---")
    
    # Экспорт данных
    st.subheader("💾 Экспорт данных")
    
    # Подготовка данных для экспорта
    export_df = create_csv_export(climate_df, stations_df)
    
    # CSV экспорт
    csv_data = export_df.to_csv(index=False, encoding='utf-8-sig')
    
    # TXT отчёт
    txt_report = generate_report_text(report)
    
    # Кнопки загрузки
    col1, col2 = st.columns(2)
    
    with col1:
        st.download_button(
            label="📥 Скачать CSV",
            data=csv_data,
            file_name=f"climatic_data_{datetime.now().strftime('%Y%m%d_%H%M')}.csv",
            mime="text/csv",
            use_container_width=True
        )
    
    with col2:
        st.download_button(
            label="📥 Скачать TXT отчёт",
            data=txt_report,
            file_name=f"climatic_report_{datetime.now().strftime('%Y%m%d_%H%M')}.txt",
            mime="text/plain",
            use_container_width=True
        )
    
    # Предпросмотр данных
    st.markdown("---")
    st.subheader("📋 Предпросмотр данных для экспорта")
    
    st.dataframe(
        export_df.head(100),
        use_container_width=True,
        hide_index=True
    )
    
    st.caption(f"Всего записей: {len(export_df)}. Показаны первые 100.")
    
    # История отчётов (демо)
    st.markdown("---")
    st.subheader("📚 История отчётов")
    
    st.info("""
    **История сгенерированных отчётов**
    
    В данной версии история не сохраняется. В production-версии здесь будет 
    отображаться список ранее сгенерированных отчётов с возможностью скачивания.
    
    - Отчёты хранятся в течение 30 дней
    - Доступна фильтрация по дате и региону
    - Возможность пакетного скачивания
    """)


if __name__ == "__main__":
    main()
