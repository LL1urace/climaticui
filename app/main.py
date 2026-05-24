from __future__ import annotations

import sys
from pathlib import Path

import streamlit as st

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.api import auth
from app.api.client import ApiError
from app.api.health import get_health
from app.components.auth_forms import render_auth_tabs
from app.components.errors import render_api_error
from app.components.layout import apply_page_background, page_title, setup_page
from app.components.sidebar import render_sidebar
from app.config import get_settings
from app.state.session import init_session_state, is_authenticated, set_current_user


setup_page("Главная")
init_session_state()
settings = get_settings()
apply_page_background(
    "app/assets/background.png",
    overlay="transparent",
    blur_px=0,
)
render_sidebar()

left, right = st.columns([0.68, 0.32], vertical_alignment="center")
with left:
    page_title(settings.app_title, "Рабочий frontend-клиент для анализа климатических данных Евразии через backend API.")
with right:
    st.image("app/assets/main_logo.png", width=182)

try:
    health = get_health()
    status = health.get("status", "ok") if isinstance(health, dict) else "ok"
    if settings.use_sample_data:
        st.info(f"Включён sample-режим: {status}. Backend не требуется для просмотра демо.")
    else:
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
st.markdown(
    f"""
    <div class="klima-hero">
        <span class="klima-kicker">Climate intelligence frontend</span>
        <h1>Добро пожаловать, {user.get('full_name') or user.get('email') or 'исследователь'}</h1>
        <p>
            «КлиматикА» превращает backend API в понятную рабочую среду:
            выбирайте станции, период и параметр, запускайте анализы, сравнения,
            прогнозы и отчёты без локальных CSV и клиентских расчётов.
        </p>
        <div class="klima-stat-strip">
            <div class="klima-stat"><strong>API</strong><span>единый источник данных</span></div>
            <div class="klima-stat"><strong>7</strong><span>аналитических сценариев</span></div>
            <div class="klima-stat"><strong>JWT</strong><span>рабочая сессия пользователя</span></div>
        </div>
    </div>
    """,
    unsafe_allow_html=True,
)

cta_left, cta_center, cta_right = st.columns([0.22, 0.56, 0.22])
with cta_center:
    if st.button("Открыть исследовательскую панель", type="primary", use_container_width=True):
        st.switch_page("pages/00_Dashboard.py")

st.subheader("Что делает приложение")
overview_cols = st.columns(3)
with overview_cols[0]:
    st.markdown(
        """
        <div class="klima-card klima-card-blue">
            <h3>Собирает контекст</h3>
            <p>Исследовательская панель хранит общий период и набор метеостанций для дальнейших страниц.</p>
        </div>
        """,
        unsafe_allow_html=True,
    )
with overview_cols[1]:
    st.markdown(
        """
        <div class="klima-card">
            <h3>Визуализирует ответы</h3>
            <p>Streamlit, Plotly и PyDeck показывают графики, таблицы, карту и JSON backend API.</p>
        </div>
        """,
        unsafe_allow_html=True,
    )
with overview_cols[2]:
    st.markdown(
        """
        <div class="klima-card klima-card-ink">
            <h3>Не считает на клиенте</h3>
            <p>Frontend остаётся тонким клиентом: климатическая статистика и отчёты выполняются backend.</p>
        </div>
        """,
        unsafe_allow_html=True,
    )
st.info("Если backend ещё не запущен, sample-режим позволяет посмотреть интерфейс и demo-данные без PostgreSQL.")
