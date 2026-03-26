"""
Модуль аутентификации и управления сессией.
Реализует полноценную систему авторизации для Streamlit.
"""

import streamlit as st
import hashlib
import base64
from utils.auth import get_user_by_id
from app.components.navbar import render_navbar
from pathlib import Path


# ============================================================================
# Констанции
# ============================================================================
SESSION_SALT = "climatic_ui_secure_salt_2026"
COOKIE_PREFIX = "climatic_"


# ============================================================================
# Вспомогательные функции
# ============================================================================

def _get_user_token(user_id: int) -> str:
    """
    Создаёт безопасный токен для пользователя.
    
    Args:
        user_id: ID пользователя
        
    Returns:
        str: MD5 хеш токена
    """
    data = f"user_{user_id}_{SESSION_SALT}"
    return hashlib.md5(data.encode()).hexdigest()


def _encode_cookie_value(value: str) -> str:
    """Кодирует значение для cookie."""
    return base64.b64encode(value.encode()).decode()


def _decode_cookie_value(encoded: str) -> str:
    """Декодирует значение из cookie."""
    try:
        return base64.b64decode(encoded.encode()).decode()
    except:
        return None


# ============================================================================
# Инициализация Session State
# ============================================================================

def init_session_state():
    """
    Инициализирует session_state для авторизации.
    Должна вызываться в начале КАЖДОЙ страницы.
    """
    if "logged_in" not in st.session_state:
        st.session_state.logged_in = False
    
    if "user" not in st.session_state:
        st.session_state.user = None
    
    if "_session_checked" not in st.session_state:
        st.session_state._session_checked = False


# ============================================================================
# Работа с Cookies через JavaScript
# ============================================================================

def _save_cookies_js(user_id: int, username: str, token: str):
    """
    Сохраняет cookies через JavaScript.
    
    Args:
        user_id: ID пользователя
        username: Имя пользователя
        token: Токен сессии
    """
    expires = "Fri, 31 Dec 2027 23:59:59 GMT"
    
    js_code = f"""
    <script>
        document.cookie = "{COOKIE_PREFIX}user_id={_encode_cookie_value(str(user_id))}; expires={expires}; path=/; SameSite=Lax";
        document.cookie = "{COOKIE_PREFIX}username={_encode_cookie_value(username)}; expires={expires}; path=/; SameSite=Lax";
        document.cookie = "{COOKIE_PREFIX}token={token}; expires={expires}; path=/; SameSite=Lax";
    </script>
    """
    st.components.v1.html(js_code, height=0)


def _load_cookies_js():
    """
    Загружает cookies через JavaScript и передаёт в query params.
    """
    js_code = f"""
    <script>
        function getCookie(name) {{
            const value = "; " + document.cookie;
            const parts = value.split("; " + name + "=");
            if (parts.length === 2) return parts.pop().split(";").shift();
        }}
        
        const user_id = getCookie("{COOKIE_PREFIX}user_id");
        const username = getCookie("{COOKIE_PREFIX}username");
        const token = getCookie("{COOKIE_PREFIX}token");
        
        if (user_id && username && token) {{
            const url = new URL(window.location.href);
            url.searchParams.set('uid', atob(user_id));
            url.searchParams.set('uname', atob(username));
            url.searchParams.set('tok', token);
            window.history.replaceState({{}}, '', url);
        }}
    </script>
    """
    st.components.v1.html(js_code, height=0)


def _delete_cookies_js():
    """Удаляет cookies через JavaScript."""
    js_code = f"""
    <script>
        document.cookie = "{COOKIE_PREFIX}user_id=; expires=Thu, 01 Jan 1970 00:00:00 GMT; path=/";
        document.cookie = "{COOKIE_PREFIX}username=; expires=Thu, 01 Jan 1970 00:00:00 GMT; path=/";
        document.cookie = "{COOKIE_PREFIX}token=; expires=Thu, 01 Jan 1970 00:00:00 GMT; path=/";
    </script>
    """
    st.components.v1.html(js_code, height=0)


# ============================================================================
# Публичные API функции
# ============================================================================

def check_and_restore_session():
    """
    Проверяет и восстанавливает сессию из cookies.
    Должна вызываться ПОСЛЕ init_session_state() в начале каждой страницы.
    
    Returns:
        bool: True если сессия восстановлена
    """
    # Проверяем только один раз за сессию приложения
    if st.session_state._session_checked:
        return st.session_state.logged_in
    
    st.session_state._session_checked = True
    
    # Загружаем cookies в query params
    _load_cookies_js()
    
    # Проверяем query params
    try:
        user_id = st.query_params.get("uid")
        username = st.query_params.get("uname")
        token = st.query_params.get("tok")
        
        if user_id and token:
            user_id = int(user_id)
            expected_token = _get_user_token(user_id)
            
            if token == expected_token:
                user_data = get_user_by_id(user_id)
                if user_data:
                    st.session_state.logged_in = True
                    st.session_state.user = user_data
                    return True
    except (ValueError, TypeError):
        pass
    
    return False


def save_session(user_id: int, username: str):
    """
    Сохраняет сессию в cookies.
    
    Args:
        user_id: ID пользователя
        username: Имя пользователя
    """
    token = _get_user_token(user_id)
    _save_cookies_js(user_id, username, token)
    
    st.session_state.logged_in = True
    st.session_state.user = get_user_by_id(user_id)


def clear_session():
    """Очищает сессию и cookies."""
    _delete_cookies_js()
    
    st.session_state.logged_in = False
    st.session_state.user = None
    
    # Очищаем query params
    try:
        del st.query_params["uid"]
        del st.query_params["uname"]
        del st.query_params["tok"]
    except:
        pass


def is_authenticated() -> bool:
    """
    Проверяет, авторизован ли пользователь.
    
    Returns:
        bool: True если авторизован
    """
    return st.session_state.get("logged_in", False) and st.session_state.get("user") is not None


def require_auth():
    """
    Требует авторизации. Если не авторизован - редиректит на login.
    Должна вызываться в начале защищённых страниц.
    """
    if not is_authenticated():
        st.switch_page("pages/0_Login.py")


def redirect_if_authenticated():
    """
    Редиректит на главную если пользователь уже авторизован.
    Должна вызываться в начале страницы login.
    """
    if is_authenticated():
        st.switch_page("app.py")


def load_css_styles():
    """
    Загружает кастомные CSS стили для фиолетово-белой темы.
    """
    css_path = Path(__file__).parent.parent / "app" / "styles.css"
    if css_path.exists():
        with open(css_path, "r", encoding="utf-8") as f:
            st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)
