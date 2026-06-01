"""Sidebar shell."""

from __future__ import annotations

import streamlit as st

from app.api.client import ApiError
from app.api.health import get_health
from app.config import get_settings
from app.state.session import clear_auth_state, is_authenticated


def render_sidebar() -> None:
    """Отображает sidebar с логотипом, пользователем и статусом API.

    Returns:
        None.
    """

    settings = get_settings()
    with st.sidebar:
        st.image("app/assets/logo.png", width=59)
        st.title(settings.app_title)
        st.caption("Frontend клиент к backend API")

        if is_authenticated():
            user = st.session_state.get("current_user") or {}
            st.divider()
            st.write(user.get("full_name") or user.get("email") or "Пользователь")
            if user.get("email"):
                st.caption(user["email"])
            st.markdown(
                """
                <style>
                section[data-testid="stSidebar"] div[data-testid="stButton"] button,
                section[data-testid="stSidebar"] div[data-testid="stButton"] button * {
                    color: #07111f !important;
                }
                section[data-testid="stSidebar"] .st-key-sidebar_logout button {
                    transition: transform .16s ease, box-shadow .16s ease, filter .16s ease !important;
                }
                section[data-testid="stSidebar"] .st-key-sidebar_logout button:hover {
                    border-color: rgba(255, 255, 255, .72) !important;
                    background: linear-gradient(135deg, #ffb020 0%, #f97316 55%, #ea580c 100%) !important;
                    box-shadow:
                        0 14px 28px rgba(234, 88, 12, .34),
                        0 0 0 4px rgba(249, 115, 22, .14) !important;
                    filter: brightness(1.05);
                    transform: translateY(-1px);
                }
                section[data-testid="stSidebar"] .st-key-sidebar_logout button:hover * {
                    color: #ffffff !important;
                }
                </style>
                """,
                unsafe_allow_html=True,
            )
            if st.button("Выйти", key="sidebar_logout", use_container_width=True):
                clear_auth_state()
                st.rerun()

        st.divider()
        if settings.use_sample_data:
            st.caption("Режим данных: `sample`")
        else:
            st.caption(f"Backend: `{settings.backend_api_url}`")
        try:
            health = get_health()
            status = health.get("status", "ok") if isinstance(health, dict) else "ok"
            st.success(f"API: {status}")
        except ApiError:
            st.warning("API недоступен")
