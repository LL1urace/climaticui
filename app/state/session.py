"""Streamlit session-state helpers for auth and user workflow state."""

from __future__ import annotations

from copy import deepcopy
from pathlib import Path

import streamlit as st


PERSISTED_FORM_VALUES_KEY = "persisted_form_values"

DEFAULT_KEYS = {
    "access_token": None,
    "current_user": None,
    "is_authenticated": False,
    "selected_station_id": None,
    "selected_parameter_id": None,
    "last_analysis_run_id": None,
    "last_analysis_result": None,
    "cached_climate_zones": None,
    "cached_stations": None,
    "cached_parameters": None,
    "cached_observation_availability": {},
    "dashboard_station_ids": None,
    "dashboard_date_from": None,
    "dashboard_date_to": None,
    "dashboard_aggregation": "monthly",
    "dashboard_filter_revision": 0,
    "dashboard_map_show_only_selected": False,
    "dashboard_map_classification_cache": {},
    "dashboard_map_classification_gradient": "climate",
    "dashboard_saved_set_mode": "dashboard",
    "last_saved_analysis_sets": [],
    "report_selected_sections": None,
    "report_include_cover": True,
    "report_include_graphs": True,
    "report_include_tables": True,
    "last_pdf_report_bytes": None,
    PERSISTED_FORM_VALUES_KEY: {},
}

DASHBOARD_CONTEXT_DEFAULTS = {
    "selected_station_id": None,
    "selected_parameter_id": None,
    "dashboard_station_ids": None,
    "dashboard_date_from": None,
    "dashboard_date_to": None,
    "dashboard_aggregation": "monthly",
    "dashboard_map_show_only_selected": False,
    "dashboard_map_classification_cache": {},
}

DASHBOARD_CONTEXT_WIDGET_KEYS = {
    "dashboard_station_multiselect",
    "dashboard_parameter",
    "dashboard_aggregation_select",
    "dashboard_period_date_from",
    "dashboard_period_date_to",
    "dashboard_map_pending_station_ids",
    "dashboard_ignore_next_map_selection",
}


def init_session_state() -> None:
    """Инициализирует обязательные ключи `st.session_state`.

    Returns:
        None.
    """

    for key, value in DEFAULT_KEYS.items():
        if key not in st.session_state:
            st.session_state[key] = deepcopy(value)


def clear_dashboard_context() -> None:
    """Сбрасывает текущий аналитический срез панели без выхода из системы.

    Returns:
        None.
    """

    init_session_state()
    persisted_values = st.session_state.get(PERSISTED_FORM_VALUES_KEY) or {}
    for key in persisted_values:
        st.session_state.pop(key, None)
    st.session_state[PERSISTED_FORM_VALUES_KEY] = {}
    for key in DASHBOARD_CONTEXT_WIDGET_KEYS:
        st.session_state.pop(key, None)
    for key in list(st.session_state):
        if str(key).startswith(("dashboard_parameter_", "dashboard_stations_map_")):
            st.session_state.pop(key, None)
    st.session_state.update(DASHBOARD_CONTEXT_DEFAULTS)


def persisted_form_value(key: str, default: object = None) -> object:
    """Возвращает сохранённое значение формы, независимое от жизненного цикла виджета."""

    init_session_state()
    values = st.session_state.get(PERSISTED_FORM_VALUES_KEY) or {}
    return values[key] if key in values else default


def remember_form_value(key: str, value: object) -> None:
    """Сохраняет значение формы между переходами по страницам Streamlit."""

    init_session_state()
    values = st.session_state.setdefault(PERSISTED_FORM_VALUES_KEY, {})
    values[key] = value


def forget_form_value(key: str) -> None:
    """Удаляет сохранённое значение формы и связанное состояние виджета."""

    init_session_state()
    values = st.session_state.setdefault(PERSISTED_FORM_VALUES_KEY, {})
    values.pop(key, None)
    st.session_state.pop(key, None)


def get_access_token() -> str | None:
    """Возвращает JWT-токен из session state.

    Returns:
        JWT-токен или None, если пользователь не авторизован.
    """

    init_session_state()
    token = st.session_state.get("access_token")
    return str(token) if token else None


def set_auth_session(access_token: str, current_user: dict | None = None) -> None:
    """Сохраняет авторизационные данные в session state.

    Args:
        access_token: JWT-токен пользователя.
        current_user: Данные текущего пользователя.

    Returns:
        None.
    """

    init_session_state()
    st.session_state["access_token"] = access_token
    st.session_state["current_user"] = current_user
    st.session_state["is_authenticated"] = True


def set_current_user(current_user: dict | None) -> None:
    """Обновляет данные текущего пользователя в session state.

    Args:
        current_user: JSON-данные пользователя или None.

    Returns:
        None.
    """

    init_session_state()
    st.session_state["current_user"] = current_user
    st.session_state["is_authenticated"] = bool(st.session_state.get("access_token") and current_user)


def clear_auth_state() -> None:
    """Очищает авторизацию и кэш справочников в session state.

    Returns:
        None.
    """

    init_session_state()
    st.session_state["access_token"] = None
    st.session_state["current_user"] = None
    st.session_state["is_authenticated"] = False
    st.session_state["cached_climate_zones"] = None
    st.session_state["cached_stations"] = None
    st.session_state["cached_parameters"] = None
    st.session_state["cached_observation_availability"] = {}


def is_authenticated() -> bool:
    """Проверяет наличие активной авторизации.

    Returns:
        True, если в session state есть JWT и флаг авторизации.
    """

    init_session_state()
    return bool(st.session_state.get("access_token") and st.session_state.get("is_authenticated"))


def require_auth() -> None:
    """Показывает экран повторного входа и останавливает защищённую страницу."""

    init_session_state()
    if is_authenticated():
        return

    from app.components.auth_forms import render_login_form

    robot_image = Path(__file__).resolve().parents[1] / "assets" / "auth_robot.png"

    st.markdown(
        """
        <style>
        .st-key-auth_guard_shell {
            overflow: hidden;
            margin: 2rem auto 0;
            padding: 1.15rem !important;
            border: 1px solid rgba(13, 100, 216, .18) !important;
            border-radius: 30px !important;
            background:
                radial-gradient(circle at 8% 10%, rgba(118, 228, 197, .38), transparent 19rem),
                radial-gradient(circle at 94% 92%, rgba(245, 158, 11, .30), transparent 18rem),
                linear-gradient(135deg, rgba(7, 17, 31, .98), rgba(10, 43, 85, .97) 54%, rgba(13, 100, 216, .94)) !important;
            box-shadow: 0 28px 72px rgba(7, 17, 31, .24) !important;
        }

        .auth-guard-copy {
            padding: .65rem 1.35rem 0;
        }

        .auth-guard-kicker {
            display: inline-flex;
            padding: .35rem .72rem;
            border: 1px solid rgba(159, 244, 223, .35);
            border-radius: 999px;
            background: rgba(118, 228, 197, .12);
            color: #9ff4df;
            font-size: .76rem;
            font-weight: 800;
            letter-spacing: .08em;
            text-transform: uppercase;
        }

        .auth-guard-copy h1 {
            max-width: 35rem;
            margin: .8rem 0 .05rem;
            color: #f97316 !important;
            font-size: clamp(2rem, 3.5vw, 3.4rem);
            line-height: .98;
        }

        .auth-guard-accent {
            display: flex;
            gap: .38rem;
            margin-top: .85rem;
        }

        .auth-guard-accent span {
            display: block;
            width: 2.4rem;
            height: .32rem;
            border-radius: 999px;
        }

        .auth-guard-accent span:nth-child(1) {
            background: #76e4c5;
        }

        .auth-guard-accent span:nth-child(2) {
            background: #38bdf8;
        }

        .auth-guard-accent span:nth-child(3) {
            background: #f59e0b;
        }

        .st-key-auth_guard_visual {
            margin: -.65rem -3rem 0 0;
            padding: .2rem 0 0;
            border-radius: 26px;
            background: radial-gradient(circle at 35% 52%, rgba(255, 255, 255, .14), transparent 52%);
        }

        .st-key-auth_guard_visual img {
            filter: drop-shadow(0 22px 22px rgba(1, 8, 20, .26));
        }

        .st-key-auth_guard_shell div[data-testid="stForm"] {
            padding: 1.25rem !important;
            border: 1px solid rgba(255, 255, 255, .72) !important;
            border-radius: 24px !important;
            background:
                radial-gradient(circle at 92% 6%, rgba(118, 228, 197, .38), transparent 10rem),
                linear-gradient(145deg, rgba(255, 255, 255, .98), rgba(226, 242, 255, .96)) !important;
            box-shadow: 0 24px 58px rgba(2, 9, 18, .28) !important;
        }

        .st-key-auth_guard_shell label,
        .st-key-auth_guard_shell label p {
            color: #12304f !important;
            font-weight: 800 !important;
        }

        .st-key-auth_guard_shell input {
            border: 1px solid rgba(13, 100, 216, .20) !important;
            background: rgba(255, 255, 255, .92) !important;
            color: #061326 !important;
        }

        .st-key-auth_guard_shell div[data-testid="stFormSubmitButton"] button {
            border: 0 !important;
            background: linear-gradient(135deg, #f59e0b, #fb7c17) !important;
            color: #ffffff !important;
        }

        .st-key-auth_guard_shell div[data-testid="stFormSubmitButton"] button * {
            color: #ffffff !important;
            font-weight: 800 !important;
        }

        .st-key-auth_guard_register button {
            margin-top: .35rem;
            border: 1px solid rgba(255, 255, 255, .72) !important;
            background: rgba(255, 255, 255, .16) !important;
            color: #ffffff !important;
        }

        .st-key-auth_guard_register button * {
            color: #ffffff !important;
            font-weight: 800 !important;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )

    with st.container(border=True, key="auth_guard_shell"):
        copy_column, login_column = st.columns([0.59, 0.41], vertical_alignment="center")
        with copy_column:
            st.markdown(
                """
                <div class="auth-guard-copy">
                    <span class="auth-guard-kicker">Сессия завершена</span>
                    <h1>Войдите снова</h1>
                    <div class="auth-guard-accent"><span></span><span></span><span></span></div>
                </div>
                """,
                unsafe_allow_html=True,
            )
            if robot_image.exists():
                with st.container(key="auth_guard_visual"):
                    st.image(str(robot_image), width=550)
        with login_column:
            render_login_form()
            if st.button("Создать аккаунт", use_container_width=True, key="auth_guard_register"):
                st.session_state["auth_default_tab"] = "Регистрация"
                st.switch_page("main.py")

    st.stop()


def remember_selection(station_id: int | str | None = None, parameter_id: int | str | None = None) -> None:
    """Запоминает выбранные станцию и параметр.

    Args:
        station_id: Идентификатор выбранной станции.
        parameter_id: Идентификатор выбранного параметра.

    Returns:
        None.
    """

    init_session_state()
    if station_id is not None:
        st.session_state["selected_station_id"] = station_id
    if parameter_id is not None:
        st.session_state["selected_parameter_id"] = parameter_id


def remember_analysis(result: dict) -> None:
    """Сохраняет последний результат анализа в session state.

    Args:
        result: JSON-ответ backend или sample API с результатом анализа.

    Returns:
        None.
    """

    init_session_state()
    analysis_run_id = result.get("analysis_run_id") or result.get("id") or result.get("run_id")
    st.session_state["last_analysis_run_id"] = analysis_run_id
    st.session_state["last_analysis_result"] = result

