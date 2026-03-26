"""
Утилита для работы с сессией пользователя.
Использует st.session_state для хранения данных.
"""

import streamlit as st
import hashlib
from utils.auth import get_user_by_id


def _get_user_token(user_id: int) -> str:
    """Создаёт токен для пользователя."""
    data = f"user_{user_id}_climatic_salt_2026"
    return hashlib.md5(data.encode()).hexdigest()


def save_session(user_id: int, username: str):
    """
    Сохраняет данные сессии в st.session_state.
    """
    st.session_state.logged_in = True
    st.session_state.user = get_user_by_id(user_id)


def load_session():
    """
    Проверяет сессию в st.session_state.
    """
    if "logged_in" not in st.session_state:
        st.session_state.logged_in = False
    if "user" not in st.session_state:
        st.session_state.user = None
    
    return st.session_state.logged_in and st.session_state.user is not None


def clear_session():
    """
    Очищает данные сессии.
    """
    st.session_state.logged_in = False
    st.session_state.user = None
