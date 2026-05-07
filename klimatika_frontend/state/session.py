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
}


def init_session_state() -> None:
    for key, value in DEFAULT_KEYS.items():
        if key not in st.session_state:
            st.session_state[key] = value


def get_access_token() -> str | None:
    init_session_state()
    token = st.session_state.get("access_token")
    return str(token) if token else None


def set_auth_session(access_token: str, current_user: dict | None = None) -> None:
    init_session_state()
    st.session_state["access_token"] = access_token
    st.session_state["current_user"] = current_user
    st.session_state["is_authenticated"] = True


def set_current_user(current_user: dict | None) -> None:
    init_session_state()
    st.session_state["current_user"] = current_user
    st.session_state["is_authenticated"] = bool(st.session_state.get("access_token") and current_user)


def clear_auth_state() -> None:
    init_session_state()
    st.session_state["access_token"] = None
    st.session_state["current_user"] = None
    st.session_state["is_authenticated"] = False
    st.session_state["cached_climate_zones"] = None
    st.session_state["cached_stations"] = None
    st.session_state["cached_parameters"] = None


def is_authenticated() -> bool:
    init_session_state()
    return bool(st.session_state.get("access_token") and st.session_state.get("is_authenticated"))


def require_auth() -> None:
    init_session_state()
    if is_authenticated():
        return

    st.warning("Для доступа к этому разделу необходимо войти в систему.")
    st.page_link("app.py", label="Перейти ко входу")
    st.stop()


def remember_selection(station_id: int | str | None = None, parameter_id: int | str | None = None) -> None:
    init_session_state()
    if station_id is not None:
        st.session_state["selected_station_id"] = station_id
    if parameter_id is not None:
        st.session_state["selected_parameter_id"] = parameter_id


def remember_analysis(result: dict) -> None:
    init_session_state()
    analysis_run_id = result.get("analysis_run_id") or result.get("id") or result.get("run_id")
    st.session_state["last_analysis_run_id"] = analysis_run_id
    st.session_state["last_analysis_result"] = result

