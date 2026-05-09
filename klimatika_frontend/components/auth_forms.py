"""Login and registration forms."""

from __future__ import annotations

import streamlit as st

from klimatika_frontend.api import auth
from klimatika_frontend.api.client import ApiError
from klimatika_frontend.components.errors import render_api_error
from klimatika_frontend.state.session import set_auth_session, set_current_user


def _extract_token(payload: dict) -> str | None:
    """Извлекает JWT-токен из ответа авторизации.

    Args:
        payload: JSON-ответ backend API на запрос входа.

    Returns:
        Токен доступа или None, если токен отсутствует.
    """

    return payload.get("access_token") or payload.get("token") or payload.get("jwt")


def _render_auth_styles() -> None:
    """Добавляет стили для непрозрачного темно-синего блока авторизации.

    Returns:
        None.
    """

    st.markdown(
        """
        <style>
        div[data-testid="stTabs"] {
            background:
                radial-gradient(circle at 85% 8%, rgba(26, 195, 220, 0.28), transparent 18rem),
                linear-gradient(135deg, #061326 0%, #08264b 54%, #0b3769 100%) !important;
            border: 1px solid rgba(255, 255, 255, 0.18) !important;
            border-radius: 28px !important;
            box-shadow: 0 28px 72px rgba(4, 12, 24, 0.36) !important;
            padding: 1.2rem 1.35rem 1.35rem !important;
        }

        div[data-testid="stTabs"] [role="tablist"] {
            border-bottom: 1px solid rgba(255, 255, 255, 0.18) !important;
            gap: 0.5rem !important;
        }

        div[data-testid="stTabs"] [role="tab"] {
            background: rgba(255, 255, 255, 0.08) !important;
            border-radius: 999px 999px 0 0 !important;
            padding: 0.55rem 1rem !important;
        }

        div[data-testid="stTabs"] [role="tab"][aria-selected="true"] {
            background: rgba(30, 196, 222, 0.24) !important;
            border-bottom-color: #8ef4ff !important;
        }

        div[data-testid="stTabs"] [role="tab"] * {
            color: #eefcff !important;
            font-weight: 800 !important;
        }

        div[data-testid="stTabs"] div[data-testid="stForm"] {
            background: transparent !important;
            border: 0 !important;
            padding: 0.3rem 0 0 !important;
        }

        div[data-testid="stTabs"] label,
        div[data-testid="stTabs"] p,
        div[data-testid="stTabs"] span {
            color: #f8fbff !important;
        }

        div[data-testid="stTabs"] input,
        div[data-testid="stTabs"] textarea {
            background: rgba(255, 255, 255, 0.96) !important;
            border: 1px solid rgba(255, 255, 255, 0.7) !important;
            color: #061326 !important;
        }

        div[data-testid="stTabs"] input::placeholder,
        div[data-testid="stTabs"] textarea::placeholder {
            color: #5b6c82 !important;
        }

        div[data-testid="stTabs"] div[data-testid="stFormSubmitButton"] button {
            background: linear-gradient(135deg, #f8fbff 0%, #baf6ff 100%) !important;
            border: 0 !important;
            box-shadow: 0 16px 36px rgba(2, 9, 18, 0.24) !important;
            color: #061326 !important;
        }

        div[data-testid="stTabs"] div[data-testid="stFormSubmitButton"] button * {
            color: #061326 !important;
            font-weight: 800 !important;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def render_auth_tabs() -> None:
    """Отображает вкладки входа и регистрации.

    Returns:
        None.
    """

    _render_auth_styles()
    login_tab, register_tab = st.tabs(["Вход", "Регистрация"])
    with login_tab:
        render_login_form()
    with register_tab:
        render_register_form()


def render_login_form() -> None:
    """Отображает форму входа и сохраняет JWT при успехе.

    Returns:
        None.
    """

    with st.form("login_form", clear_on_submit=False):
        email = st.text_input("Email")
        password = st.text_input("Пароль", type="password")
        submitted = st.form_submit_button("Войти", use_container_width=True)

    if not submitted:
        return
    if not email or not password:
        st.error("Введите email и пароль.")
        return

    try:
        response = auth.login(email=email, password=password)
        token = _extract_token(response)
        if not token:
            st.error("Backend не вернул JWT token.")
            return
        set_auth_session(token)
        try:
            set_current_user(auth.get_current_user())
        except ApiError:
            set_current_user({"email": email})
        st.success("Вход выполнен.")
        st.rerun()
    except ApiError as error:
        render_api_error(error)


def render_register_form() -> None:
    """Отображает форму регистрации пользователя через backend API.

    Returns:
        None.
    """

    with st.form("register_form", clear_on_submit=True):
        full_name = st.text_input("Полное имя")
        email = st.text_input("Email", key="register_email")
        password = st.text_input("Пароль", type="password", key="register_password")
        submitted = st.form_submit_button("Зарегистрироваться", use_container_width=True)

    if not submitted:
        return
    if not full_name or not email or not password:
        st.error("Заполните имя, email и пароль.")
        return
    if len(password) < 6:
        st.error("Пароль должен быть не короче 6 символов.")
        return

    try:
        auth.register(email=email, password=password, full_name=full_name)
        st.success("Регистрация выполнена. Теперь войдите в систему.")
    except ApiError as error:
        render_api_error(error)

