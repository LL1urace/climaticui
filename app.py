"""
ClimaticUI - Главное приложение
Frontend система анализа климатических данных

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
    page_title="ClimaticUI - Анализ климатических данных",
    page_icon="🌤️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Добавляем корень проекта в sys.path
project_root = Path(__file__).parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

# Импорты
from utils.data_loader import load_stations, load_climate_data
from app.components.navbar import render_navbar
from utils.auth_session import (
    init_session_state,
    check_and_restore_session,
    require_auth,
    clear_session,
    load_css_styles
)


def load_css_styles():
    """
    Загружает кастомные CSS стили для фиолетово-белой темы.
    """
    css_path = Path(__file__).parent / "styles.css"
    if css_path.exists():
        with open(css_path, "r", encoding="utf-8") as f:
            st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)


def initialize_session_state():
    """
    Инициализирует переменные состояния сессии.
    """
    # 2. Инициализация session_state
    init_session_state()
    
    # Выбранный регион для фильтрации данных
    if 'selected_region' not in st.session_state:
        st.session_state.selected_region = 'Все регионы'

    # Диапазон дат для анализа
    if 'date_range' not in st.session_state:
        st.session_state.date_range = None

    # Выбранные метрики для отображения
    if 'selected_metrics' not in st.session_state:
        st.session_state.selected_metrics = ['temperature_c', 'humidity_pct']

    # Кэш загруженных данных
    if 'loaded_data' not in st.session_state:
        st.session_state.loaded_data = False

    # Источник данных (Mock CSV или Live API)
    if 'data_source' not in st.session_state:
        st.session_state.data_source = 'Mock CSV'


def configure_sidebar():
    """
    Настраивает боковую панель с настройками.
    """
    with st.sidebar:
        # Заголовок боковой панели
        st.title("⚙️ Настройки")
        st.markdown("---")

        # Информация о пользователе
        if st.session_state.logged_in and st.session_state.user:
            user = st.session_state.user
            st.markdown(f"**👤 {user['full_name']}**")
            st.markdown(f"*{user['username']}*")
            st.markdown(f"*{user['email']}*")
            st.markdown("---")

            # 7. Кнопка выхода
            if st.button("🚪 Выйти", use_container_width=True):
                clear_session()
                st.rerun()
        
        st.markdown("---")

        # Настройки источника данных
        st.subheader("📊 Источник данных")
        
        data_sources = ['Mock CSV', 'Live API (скоро)']
        st.session_state.data_source = st.selectbox(
            "Источник данных:",
            options=data_sources,
            index=data_sources.index(st.session_state.data_source)
        )
        
        # Фильтры
        st.markdown("---")
        st.subheader("🔍 Фильтры")
        
        # Регион
        regions = ['Все регионы', 'Central', 'North-West', 'Central Asia', 'East Asia']
        st.session_state.selected_region = st.selectbox(
            "Регион:",
            options=regions,
            index=0
        )
        
        # Метрики
        metrics = ['Температура (°C)', 'Влажность (%)', 'Давление (гПа)', 
                  'Скорость ветра (м/с)', 'Осадки (мм)']
        st.session_state.selected_metrics = st.multiselect(
            "Метрики:",
            options=metrics,
            default=['Температура (°C)', 'Влажность (%)']
        )
        
        # Информация о приложении
        st.markdown("---")
        st.markdown("**ClimaticUI v0.2.0**")
        st.markdown("Система анализа климатических данных")
        st.markdown("Евразия | 2023-2024")


def check_data_status() -> tuple:
    """
    Проверяет статус загрузки данных.

    Returns:
        tuple: (stations_loaded: bool, climate_data_loaded: bool)
    """
    stations = load_stations()
    climate_data = load_climate_data()

    stations_loaded = not stations.empty
    climate_loaded = not climate_data.empty

    return stations_loaded, climate_loaded


def main():
    """
    Основная функция приложения.
    Точка входа для Streamlit.
    """
    # Загрузка кастомных стилей
    load_css_styles()

    # 2. Инициализация session_state
    initialize_session_state()

    # 3. Восстановление сессии из cookies
    check_and_restore_session()

    # 5. Защита страницы - если не авторизован, редирект на login
    require_auth()

    # 4. Отображение навигации
    render_navbar()

    # Настройка боковой панели
    configure_sidebar()

    # Заголовок главной страницы
    st.title("🌤️ ClimaticUI")
    st.markdown("**Система анализа климатических данных для региона Евразии**")
    st.markdown("---")

    # Проверка статуса данных
    stations_loaded, climate_loaded = check_data_status()

    if stations_loaded and climate_loaded:
        st.session_state.loaded_data = True

        # Блок с краткой информацией
        col1, col2, col3 = st.columns(3)

        with col1:
            st.metric(
                label="📍 Метеостанций",
                value=len(load_stations()),
                delta=None
            )

        with col2:
            climate_df = load_climate_data()
            st.metric(
                label="📊 Записей данных",
                value=len(climate_df),
                delta=None
            )

        with col3:
            st.metric(
                label="📅 Период",
                value=f"{climate_df['date'].min().strftime('%d.%m.%Y')} - {climate_df['date'].max().strftime('%d.%m.%Y')}",
                delta=None
            )

        st.markdown("---")

        # Основная информация
        st.subheader("👋 Добро пожаловать в ClimaticUI!")

        st.markdown("""
        **ClimaticUI** — это современный интерфейс для визуализации и анализа метеорологических данных.

        ### 🎯 Возможности системы:

        - **📊 Dashboard** — сводные показатели и ключевые метрики
        - **🗺️ Карта** — интерактивная карта метеостанций Евразии
        - **📈 Аналитика** — временные ряды и сравнение периодов
        - **🔮 Прогноз** — визуализация результатов прогнозирования
        - **📑 Отчёты** — генерация и экспорт отчётов

        ### 📁 Источник данных:
        На текущем этапе используются тестовые CSV файлы из папки `/data`.

        ### 💡 Как начать работу:
        1. Выберите интересующий раздел в верхней навигационной панели
        2. Настройте параметры фильтрации в sidebar
        3. Изучите визуализации и экспортируйте данные
        """)

        # Статус подключения
        st.success("✅ Данные загружены и готовы к работе")

    else:
        # Ошибка загрузки данных
        st.error("⚠️ Ошибка загрузки данных")

        if not stations_loaded:
            st.warning("Не удалось загрузить данные о метеостанциях")

        if not climate_loaded:
            st.warning("Не удалось загрузить климатические данные")

        st.info("""
        ### Проверьте:
        1. Файлы `stations_coordinates.csv` и `climate_data_sample.csv`
           находятся в папке `/data`
        2. Файлы имеют правильную структуру колонок
        3. Файлы не пусты и не повреждены
        """)


if __name__ == "__main__":
    main()
