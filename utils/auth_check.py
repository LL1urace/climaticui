"""
Утилита для проверки авторизации пользователя.
Используется на всех страницах приложения.
"""

import streamlit as st


def check_auth():
    """
    Проверяет, авторизован ли пользователь.
    Если нет - перенаправляет на страницу входа.
    
    Возвращает данные пользователя если авторизован.
    """
    if 'logged_in' not in st.session_state:
        st.session_state.logged_in = False
    
    if 'user' not in st.session_state:
        st.session_state.user = None
    
    if not st.session_state.logged_in or not st.session_state.user:
        st.warning("🔐 Для доступа к этой странице необходимо войти в систему")
        st.link_button("Перейти ко входу", "0_Login")
        st.stop()
    
    return st.session_state.user
