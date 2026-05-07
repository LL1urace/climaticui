"""Shared page layout and styling."""

from __future__ import annotations

import streamlit as st

from klimatika_frontend.config import get_settings


def setup_page(page_title: str, icon: str = "K") -> None:
    settings = get_settings()
    st.set_page_config(
        page_title=f"{page_title} - {settings.app_title}",
        page_icon=icon,
        layout="wide",
        initial_sidebar_state="expanded",
    )
    apply_global_styles()


def apply_global_styles() -> None:
    st.markdown(
        """
        <style>
        [data-testid="stSidebarNav"] { display: none; }
        .stApp {
            background:
                linear-gradient(180deg, rgba(246, 249, 250, .96), rgba(255, 255, 255, .98)),
                url("assets/background.png");
            background-size: cover;
        }
        .block-container {
            padding-top: 2rem;
            padding-bottom: 3rem;
            max-width: 1280px;
        }
        h1, h2, h3 {
            letter-spacing: 0;
            color: #15384a;
        }
        [data-testid="stMetric"] {
            background: #ffffff;
            border: 1px solid #dce7ea;
            border-radius: 8px;
            padding: .85rem 1rem;
        }
        .stButton > button, .stDownloadButton > button {
            border-radius: 8px;
            border: 1px solid #1c5b75;
        }
        .stButton > button[kind="primary"] {
            background: #1c5b75;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def page_title(title: str, caption: str | None = None) -> None:
    st.title(title)
    if caption:
        st.caption(caption)

