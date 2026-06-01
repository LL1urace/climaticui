"""Streamlit session-state helpers for auth and user workflow state."""

from __future__ import annotations

import streamlit as st


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
    "dashboard_map_show_only_selected": False,
    "dashboard_map_classification_cache": {},
    "dashboard_saved_set_mode": "dashboard",
    "last_saved_analysis_sets": [],
    "report_selected_sections": None,
    "report_include_cover": True,
    "report_include_graphs": True,
    "report_include_tables": True,
    "last_pdf_report_bytes": None,
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
            st.session_state[key] = value


def clear_dashboard_context() -> None:
    """Сбрасывает текущий аналитический срез панели без выхода из системы.

    Returns:
        None.
    """

    init_session_state()
    for key in DASHBOARD_CONTEXT_WIDGET_KEYS:
        st.session_state.pop(key, None)
    for key in list(st.session_state):
        if str(key).startswith("dashboard_stations_map_"):
            st.session_state.pop(key, None)
    st.session_state.update(DASHBOARD_CONTEXT_DEFAULTS)


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


from pathlib import Path

def require_auth() -> None:
    """Останавливает рендер страницы, если пользователь не авторизован."""

    init_session_state()
    if is_authenticated():
        return

    robot_image = Path(__file__).resolve().parents[1] / "assets" / "auth_robot.png"

    st.markdown(
        """
        <style>
        h1 {
            color: #062245 !important;
            font-weight: 900 !important;
            text-align: center !important;
        }

        .st-key-auth_guard_login button {
            min-height: 3.4rem !important;
            background: linear-gradient(135deg, #ffb020 0%, #f97316 55%, #ea580c 100%) !important;
            border: 1px solid rgba(255, 255, 255, .78) !important;
            box-shadow:
                0 14px 30px rgba(234, 88, 12, .28),
                0 0 0 4px rgba(249, 115, 22, .12) !important;
            color: #ffffff !important;
            font-weight: 900 !important;
            font-size: 1.02rem !important;
        }

        .st-key-auth_guard_login button * {
            color: #ffffff !important;
            font-weight: 900 !important;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )

    st.write("")
    st.write("")

    img_left, img_center, img_right = st.columns([0.25, 0.5, 0.25])
    with img_center:
        if robot_image.exists():
            st.image(str(robot_image), use_container_width=True)
        else:
            st.warning(f"Картинка не найдена: {robot_image}")

    st.title("Войдите, чтобы открыть исследовательскую панель")

    st.info(
        "Эта страница доступна только авторизованным пользователям. "
        "После входа вы сможете работать с картой станций, аналитикой, "
        "историей запусков и отчётами."
    )

    st.caption("Робот-климатолог уже приготовил графики, но без входа показывать их стесняется.")

    st.write("")
    st.write("")

    left, center, right = st.columns([0.32, 0.36, 0.32])
    with center:
        if st.button("🔑 Перейти ко входу", use_container_width=True, key="auth_guard_login"):
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

