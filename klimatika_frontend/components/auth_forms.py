"""Login and registration forms."""

from __future__ import annotations

import streamlit as st

from klimatika_frontend.api import auth
from klimatika_frontend.api.client import ApiError
from klimatika_frontend.components.errors import render_api_error
from klimatika_frontend.state.session import set_auth_session, set_current_user


def _extract_token(payload: dict) -> str | None:
    return payload.get("access_token") or payload.get("token") or payload.get("jwt")


def render_auth_tabs() -> None:
    login_tab, register_tab = st.tabs(["Вход", "Регистрация"])
    with login_tab:
        render_login_form()
    with register_tab:
        render_register_form()


def render_login_form() -> None:
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

