"""
Компонент верхней навигационной панели (Navbar)
"""

import streamlit as st


def render_navbar():
    """
    Отображает верхнюю навигационную панель с фиолетовым градиентом.
    """
    # CSS для стилизации
    navbar_css = """
    <style>
    /* Скрываем стандартный header Streamlit */
    header {visibility: hidden;}
    
    /* Стили для ссылок навигации */
    .stPageLink a {
        color: rgba(255, 255, 255, 0.9) !important;
    }
    
    .stPageLink a:hover {
        background: rgba(255, 255, 255, 0.2) !important;
        color: white !important;
    }
    
    /* Убираем отступы у контейнера navbar */
    .stVerticalBlock:has(.navbar-wrapper) {
        gap: 0;
        margin: 0;
        padding: 0;
    }
    
    /* Показываем и стилизуем стандартную кнопку sidebar */
    button[title="Sidebar"], button[data-testid="stSidebarToggleButton"] {
        display: block !important;
        position: fixed;
        top: 0.8rem;
        left: 0.8rem;
        z-index: 10000;
        background: rgba(255, 255, 255, 0.2) !important;
        border: 2px solid rgba(255, 255, 255, 0.3) !important;
        color: white !important;
        font-size: 1.2rem !important;
        padding: 0.3rem 0.5rem !important;
        border-radius: 0.5rem !important;
        min-width: 2.5rem !important;
        height: 2.5rem !important;
    }
    button[title="Sidebar"]:hover, button[data-testid="stSidebarToggleButton"]:hover {
        background: rgba(255, 255, 255, 0.3) !important;
        border-color: white !important;
    }
    </style>
    """
    
    st.markdown(navbar_css, unsafe_allow_html=True)
    
    # Навигация для авторизованных и неавторизованных
    is_logged_in = st.session_state.get("logged_in", False)
    user = st.session_state.get("user", None)
    
    # Создаём навигационную панель через колонки с фиолетовым фоном
    st.markdown("""
    <style>
    .navbar-wrapper {
        background: linear-gradient(90deg, #5b21b6 0%, #7c3aed 50%, #a78bfa 100%);
        padding: 0.75rem 1rem;
        border-radius: 0;
        margin: 0;
        margin-left: -1rem;
        margin-right: -1rem;
        width: calc(100% + 2rem);
    }
    </style>
    """, unsafe_allow_html=True)
    
    st.markdown('<div class="navbar-wrapper">', unsafe_allow_html=True)
    
    # Колонки для навигации
    if is_logged_in and user:
        col_brand, col_nav, col_user = st.columns([1, 5, 1], gap="small")
    else:
        col_brand, col_nav, col_user = st.columns([1, 3, 1], gap="small")
    
    with col_brand:
        st.markdown(
            '<div style="font-size: 1.5rem; font-weight: bold; color: white; display: flex; align-items: center; gap: 0.5rem;">'
            '🌤️ ClimaticUI</div>',
            unsafe_allow_html=True
        )
    
    with col_nav:
        # Навигационные ссылки
        if is_logged_in and user:
            # Меню для авторизованных пользователей
            cols = st.columns(7, gap="small")
            pages = [
                ("app.py", "🏠 Главная"),
                ("pages/1_Dashboard.py", "📊 Dashboard"),
                ("pages/2_Map_View.py", "🗺️ Карта"),
                ("pages/3_Analytics.py", "📈 Аналитика"),
                ("pages/4_Forecast.py", "🔮 Прогноз"),
                ("pages/5_Reports.py", "📑 Отчёты"),
                ("pages/Profile.py", "👤 Профиль"),
            ]
            
            for i, (page_path, label) in enumerate(pages):
                with cols[i]:
                    st.page_link(page_path, label=label)
        else:
            # Меню для неавторизованных
            cols = st.columns(3, gap="small")
            pages = [
                ("app.py", "🏠 Главная"),
                ("pages/0_Login.py", "🔐 Вход"),
                ("pages/Register.py", "📝 Регистрация"),
            ]
            
            for i, (page_path, label) in enumerate(pages):
                with cols[i]:
                    st.page_link(page_path, label=label)
    
    with col_user:
        if is_logged_in and user:
            st.markdown(
                f'<div style="text-align: right; color: white; font-weight: 600; padding-top: 0.5rem;">'
                f'👤 {user.get("full_name", user.get("username", "User"))}</div>',
                unsafe_allow_html=True
            )
        else:
            st.markdown("")
    
    st.markdown('</div>', unsafe_allow_html=True)
