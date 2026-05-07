from __future__ import annotations

import streamlit as st

from klimatika_frontend.api import auth
from klimatika_frontend.api.client import ApiError
from klimatika_frontend.api.health import get_health
from klimatika_frontend.components.auth_forms import render_auth_tabs
from klimatika_frontend.components.errors import render_api_error
from klimatika_frontend.components.layout import page_title, setup_page
from klimatika_frontend.components.sidebar import render_sidebar
from klimatika_frontend.config import get_settings
from klimatika_frontend.state.session import init_session_state, is_authenticated, set_current_user


setup_page("Главная")
init_session_state()
settings = get_settings()
render_sidebar()

left, right = st.columns([0.72, 0.28], vertical_alignment="center")
with left:
    page_title(settings.app_title, "Рабочий frontend-клиент для анализа климатических данных Евразии через backend API.")
with right:
    st.image("assets/logo.png", width=150)

try:
    health = get_health()
    status = health.get("status", "ok") if isinstance(health, dict) else "ok"
    st.success(f"Backend API доступен: {status}")
except ApiError as error:
    render_api_error(error)

if not is_authenticated():
    st.subheader("Авторизация")
    render_auth_tabs()
    st.stop()

if st.session_state.get("current_user") is None:
    try:
        set_current_user(auth.get_current_user())
    except ApiError as error:
        render_api_error(error)

user = st.session_state.get("current_user") or {}
st.subheader(f"Добро пожаловать, {user.get('full_name') or user.get('email') or 'исследователь'}")
st.write("Выберите рабочий раздел. Все данные, расчёты, история и отчёты запрашиваются только через backend API.")

cols = st.columns(4)
with cols[0]:
    st.page_link("pages/01_Анализ.py", label="Анализ", icon="📈")
    st.page_link("pages/02_Сравнение_периодов.py", label="Сравнение периодов", icon="🧭")
with cols[1]:
    st.page_link("pages/03_Сравнение_станций.py", label="Сравнение станций", icon="📍")
    st.page_link("pages/04_Климатограмма.py", label="Климатограмма", icon="🌦️")
with cols[2]:
    st.page_link("pages/05_Прогнозирование.py", label="Прогнозирование", icon="🔮")
    st.page_link("pages/06_История_анализов.py", label="История анализов", icon="🗂️")
with cols[3]:
    st.page_link("pages/07_Отчёты.py", label="Отчёты", icon="📄")

st.info("Frontend не читает локальные CSV и не выполняет климатические расчёты. Все вычисления остаются на backend.")
