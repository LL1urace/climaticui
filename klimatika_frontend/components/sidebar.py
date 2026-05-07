"""Sidebar shell."""

from __future__ import annotations

import streamlit as st

from klimatika_frontend.api.client import ApiError
from klimatika_frontend.api.health import get_health
from klimatika_frontend.config import get_settings
from klimatika_frontend.state.session import clear_auth_state, is_authenticated


def render_sidebar() -> None:
    settings = get_settings()
    with st.sidebar:
        st.image("assets/logo.png", width=84)
        st.title(settings.app_title)
        st.caption("Frontend клиент к backend API")

        if is_authenticated():
            user = st.session_state.get("current_user") or {}
            st.divider()
            st.write(user.get("full_name") or user.get("email") or "Пользователь")
            if user.get("email"):
                st.caption(user["email"])
            if st.button("Выйти", use_container_width=True):
                clear_auth_state()
                st.rerun()

        st.divider()
        st.caption(f"Backend: `{settings.backend_api_url}`")
        try:
            health = get_health()
            status = health.get("status", "ok") if isinstance(health, dict) else "ok"
            st.success(f"API: {status}")
        except ApiError:
            st.warning("API недоступен")
