"""Shared page layout and styling."""

from __future__ import annotations

from base64 import b64encode
from pathlib import Path

import streamlit as st

from klimatika_frontend.config import get_settings


def setup_page(page_title: str, icon: str = "K") -> None:
    """Настраивает страницу Streamlit и применяет общие стили.

    Args:
        page_title: Заголовок текущей страницы.
        icon: Иконка страницы.

    Returns:
        None.
    """

    settings = get_settings()
    st.set_page_config(
        page_title=f"{page_title} - {settings.app_title}",
        page_icon=icon,
        layout="wide",
        initial_sidebar_state="expanded",
    )
    apply_global_styles()


def apply_global_styles() -> None:
    """Добавляет глобальные CSS-стили Streamlit-приложения.

    Returns:
        None.
    """

    st.markdown(
        """
        <style>
        @import url('https://fonts.googleapis.com/css2?family=IBM+Plex+Sans:wght@400;500;600;700&family=Manrope:wght@500;600;700;800&display=swap');

        :root {
            --klima-ink: #07111f;
            --klima-ink-soft: #12233a;
            --klima-blue: #0d64d8;
            --klima-blue-soft: #dbeafe;
            --klima-cyan: #17b6d6;
            --klima-mint: #76e4c5;
            --klima-sand: #f7efe0;
            --klima-card: rgba(255, 255, 255, .92);
            --klima-border: rgba(7, 17, 31, .10);
        }

        [data-testid="stSidebarNav"] { display: none; }
        .stApp {
            background:
                radial-gradient(circle at top left, rgba(23, 182, 214, .24), transparent 28rem),
                radial-gradient(circle at 82% 8%, rgba(13, 100, 216, .20), transparent 24rem),
                linear-gradient(135deg, rgba(247, 239, 224, .96), rgba(240, 248, 255, .98) 44%, rgba(255, 255, 255, .98)),
                url("assets/background.png");
            background-size: cover;
            color: var(--klima-ink);
            font-family: 'IBM Plex Sans', 'Segoe UI', sans-serif;
        }
        .block-container {
            padding-top: 2rem;
            padding-bottom: 3rem;
            max-width: 1280px;
        }
        section[data-testid="stSidebar"] {
            background:
                linear-gradient(180deg, rgba(7, 17, 31, .96), rgba(16, 42, 72, .96)),
                url("assets/background.png");
            color: #f8fbff;
        }
        section[data-testid="stSidebar"] h1,
        section[data-testid="stSidebar"] h2,
        section[data-testid="stSidebar"] h3,
        section[data-testid="stSidebar"] p,
        section[data-testid="stSidebar"] span,
        section[data-testid="stSidebar"] label {
            color: #f8fbff;
        }
        h1, h2, h3 {
            letter-spacing: -.035em;
            color: var(--klima-ink);
            font-family: 'Manrope', 'IBM Plex Sans', sans-serif;
            font-weight: 800;
        }
        p, label, span, div {
            font-family: 'IBM Plex Sans', 'Segoe UI', sans-serif;
        }
        [data-testid="stMetric"] {
            background: var(--klima-card);
            border: 1px solid var(--klima-border);
            border-radius: 18px;
            padding: .85rem 1rem;
            box-shadow: 0 18px 40px rgba(7, 17, 31, .08);
        }
        .stButton > button, .stDownloadButton > button {
            border-radius: 999px;
            border: 1px solid rgba(7, 17, 31, .14);
            font-weight: 700;
            box-shadow: 0 10px 26px rgba(13, 100, 216, .14);
        }
        .stButton > button[kind="primary"] {
            background: linear-gradient(135deg, var(--klima-blue), var(--klima-cyan));
            border: 0;
        }
        [data-testid="stPageLink"] a {
            display: flex;
            align-items: center;
            justify-content: flex-start;
            width: 100%;
            min-height: 3.15rem;
            box-sizing: border-box;
            background: rgba(255, 255, 255, .86);
            border: 1px solid rgba(13, 100, 216, .16);
            border-radius: 16px;
            padding: .7rem .85rem;
            margin: .25rem 0;
            box-shadow: 0 12px 28px rgba(7, 17, 31, .07);
            transition: transform .16s ease, box-shadow .16s ease, border-color .16s ease;
        }
        [data-testid="stPageLink"] a:hover {
            border-color: rgba(13, 100, 216, .55);
            box-shadow: 0 18px 40px rgba(13, 100, 216, .16);
            transform: translateY(-1px);
        }
        .klima-hero {
            position: relative;
            overflow: hidden;
            border-radius: 32px;
            padding: 2.4rem;
            color: #f8fbff;
            background:
                radial-gradient(circle at 78% 20%, rgba(118, 228, 197, .42), transparent 18rem),
                linear-gradient(135deg, #07111f 0%, #0a2b55 52%, #0d64d8 100%);
            box-shadow: 0 28px 70px rgba(7, 17, 31, .22);
        }
        .klima-hero h1,
        .klima-hero h2,
        .klima-hero p {
            color: #f8fbff;
        }
        .klima-hero h1 {
            font-size: clamp(2.4rem, 5vw, 4.8rem);
            line-height: .96;
            margin: .25rem 0 1rem;
        }
        .klima-kicker {
            display: inline-flex;
            align-items: center;
            gap: .45rem;
            padding: .35rem .8rem;
            border-radius: 999px;
            background: rgba(255, 255, 255, .12);
            border: 1px solid rgba(255, 255, 255, .20);
            color: #c8f7ff;
            font-weight: 700;
            text-transform: uppercase;
            letter-spacing: .08em;
            font-size: .76rem;
        }
        .klima-card {
            height: 100%;
            padding: 1.15rem;
            border-radius: 22px;
            background: var(--klima-card);
            border: 1px solid var(--klima-border);
            box-shadow: 0 18px 46px rgba(7, 17, 31, .08);
        }
        .klima-card h3 {
            margin-top: 0;
            margin-bottom: .45rem;
            font-size: 1.05rem;
        }
        .klima-card p {
            color: #39536f;
            margin-bottom: 0;
        }
        .klima-feature-card {
            height: 16rem;
            display: flex;
            flex-direction: column;
            justify-content: flex-start;
            padding-bottom: 5.6rem;
            margin-bottom: 0;
            box-sizing: border-box;
        }
        div[data-testid="stColumn"] > div:has(.klima-feature-card) .stButton {
            margin-top: -5rem;
            padding: 0 1.15rem;
            position: relative;
            z-index: 2;
        }
        div[data-testid="stColumn"] > div:has(.klima-feature-card) div[data-testid="stHorizontalBlock"]:has(.stButton) {
            margin-top: -5rem;
            padding: 0 1.15rem;
            position: relative;
            z-index: 2;
        }
        div[data-testid="stColumn"] > div:has(.klima-feature-card) div[data-testid="stHorizontalBlock"]:has(.stButton) .stButton {
            margin-top: 0;
            padding: 0;
        }
        div[data-testid="stColumn"] > div:has(.klima-feature-card) .stButton > button {
            width: 100%;
            min-height: 2.5rem;
            background: rgba(255, 255, 255, .94);
            color: #07111f;
            border: 1px solid rgba(255, 255, 255, .40);
            box-shadow: 0 10px 28px rgba(7, 17, 31, .16);
        }
        .klima-card-blue {
            background: linear-gradient(135deg, #0d64d8, #17b6d6);
            color: #f8fbff;
            border: 0;
        }
        .klima-card-blue h3,
        .klima-card-blue p {
            color: #f8fbff;
        }
        .klima-card-ink {
            background: linear-gradient(135deg, #07111f, #17233a);
            color: #f8fbff;
            border: 0;
        }
        .klima-card-ink h3,
        .klima-card-ink p,
        .klima-card-ink strong,
        .klima-card-ink span {
            color: #f8fbff;
        }
        .klima-stat-strip {
            display: grid;
            grid-template-columns: repeat(3, minmax(0, 1fr));
            gap: .85rem;
            margin: 1rem 0 1.3rem;
        }
        .klima-stat {
            padding: .95rem;
            border-radius: 18px;
            background: rgba(255, 255, 255, .12);
            border: 1px solid rgba(255, 255, 255, .18);
        }
        .klima-stat strong {
            display: block;
            color: #ffffff;
            font-size: 1.55rem;
            font-family: 'Manrope', sans-serif;
        }
        .klima-stat span {
            color: #c8f7ff;
            font-weight: 600;
        }
        .klima-feature-grid {
            display: grid;
            grid-template-columns: repeat(3, minmax(0, 1fr));
            gap: 1rem;
        }
        @media (max-width: 900px) {
            .klima-stat-strip,
            .klima-feature-grid {
                grid-template-columns: 1fr;
            }
            .klima-feature-card {
                height: auto;
                min-height: 14rem;
            }
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def page_title(title: str, caption: str | None = None) -> None:
    """Отображает заголовок и краткое описание страницы.

    Args:
        title: Основной заголовок страницы.
        caption: Дополнительное описание под заголовком.

    Returns:
        None.
    """

    st.title(title)
    if caption:
        st.caption(caption)


def apply_page_background(
    image_path: str,
    overlay: str = "linear-gradient(180deg, rgba(248, 252, 255, .76), rgba(248, 252, 255, .90))",
    blur_px: float = 0,
    image_opacity: float = 0.32,
    base_background: str = (
        "radial-gradient(circle at top left, rgba(23, 182, 214, .24), transparent 28rem), "
        "radial-gradient(circle at 82% 8%, rgba(13, 100, 216, .20), transparent 24rem), "
        "linear-gradient(135deg, rgba(247, 239, 224, .96), rgba(240, 248, 255, .98) 44%, rgba(255, 255, 255, .98))"
    ),
) -> None:
    """Применяет фоновое изображение к текущей странице Streamlit.

    Args:
        image_path: Путь к PNG-изображению относительно корня проекта.
        overlay: CSS-градиент поверх изображения для читаемости контента.
        blur_px: Радиус размытия фонового изображения в пикселях.
        image_opacity: Прозрачность фонового изображения от 0 до 1.
        base_background: Базовый CSS-фон под изображением.

    Returns:
        None.
    """

    path = Path(image_path)
    if not path.exists():
        return

    encoded = b64encode(path.read_bytes()).decode("ascii")
    blur_inset = max(12, blur_px * 4)
    st.markdown(
        f"""
        <style>
        .stApp {{
            position: relative !important;
            isolation: isolate !important;
            background: {base_background} !important;
            min-height: 100dvh !important;
            height: 100dvh !important;
            overflow-x: hidden !important;
            overflow-y: hidden !important;
        }}
        html,
        body,
        #root {{
            height: 100% !important;
            overflow: hidden !important;
        }}
        .stApp [data-testid="stAppViewContainer"] {{
            height: 100dvh !important;
            min-height: 100dvh !important;
            overflow: hidden !important;
        }}
        .stApp [data-testid="stMain"],
        .stApp section.main {{
            height: 100dvh !important;
            max-height: 100dvh !important;
            overflow-y: auto !important;
            overflow-x: hidden !important;
            overscroll-behavior: contain !important;
        }}
        .stApp::before {{
            content: "";
            position: fixed;
            inset: -{blur_inset}px;
            z-index: 0;
            pointer-events: none;
            background-image: url("data:image/png;base64,{encoded}");
            background-position: center center;
            background-size: cover;
            background-repeat: no-repeat;
            opacity: {image_opacity};
            filter: blur({blur_px}px);
            transform: scale(1.04);
        }}
        .stApp::after {{
            content: "";
            position: fixed;
            inset: 0;
            z-index: 1;
            pointer-events: none;
            background: {overlay};
        }}
        .stApp > * {{
            position: relative;
            z-index: 2;
        }}
        .stApp [data-testid="stAppViewContainer"] {{
            overflow-x: hidden !important;
        }}
        .stApp .block-container,
        .stApp [data-testid="stMainBlockContainer"] {{
            padding-bottom: .75rem !important;
        }}
        </style>
        """,
        unsafe_allow_html=True,
    )


def render_home_button(label: str = "К исследовательской панели", target_page: str = "pages/00_Dashboard.py") -> None:
    """Отображает кнопку перехода на целевую страницу навигации.

    Args:
        label: Текст кнопки возврата.
        target_page: Путь страницы Streamlit для перехода.

    Returns:
        None.
    """

    if st.button(label, key="go_home_button"):
        st.switch_page(target_page)
