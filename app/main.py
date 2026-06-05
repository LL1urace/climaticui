from __future__ import annotations

from html import escape
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


def _format_count(value: int) -> str:
    """Форматирует целое число с пробелами между разрядами."""

    return f"{value:,}".replace(",", " ")


def _sample_dataset_summary() -> dict[str, str]:
    """Возвращает актуальную сводку локального демонстрационного набора."""

    from app.sample.data import ARCTIC_MONTHLY_ROWS, PARAMETERS, REAL_MONTHLY_STATION_IDS, STATIONS

    years = sorted({str(row.get("date", ""))[:4] for row in ARCTIC_MONTHLY_ROWS if row.get("date")})
    period = f"{years[0]}–{years[-1]}" if years else "demo"
    return {
        "stations": _format_count(len(STATIONS)),
        "countries": _format_count(len({station.get("country") for station in STATIONS if station.get("country")})),
        "parameters": _format_count(len(PARAMETERS)),
        "real_stations": _format_count(len(REAL_MONTHLY_STATION_IDS)),
        "period": period,
    }


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
    page_title(settings.app_title, "Рабочее пространство для анализа климатических данных метеостанций через backend API.")
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
    render_auth_tabs(default_tab=st.session_state.pop("auth_default_tab", None))
    st.stop()

if st.session_state.get("current_user") is None:
    try:
        set_current_user(auth.get_current_user())
    except ApiError as error:
        render_api_error(error)

user = st.session_state.get("current_user") or {}
display_name = escape(str(user.get("full_name") or user.get("email") or "исследователь"))
dataset = _sample_dataset_summary() if settings.use_sample_data else None
hero_station_value = dataset["stations"] if dataset else "API"
hero_period_value = dataset["period"] if dataset else "live"
hero_period_caption = "период реальных demo-рядов" if dataset else "период определяется backend"

st.markdown(
    """
    <style>
    .st-key-home-hero {
        position: relative;
        overflow: hidden;
        min-height: 31rem;
        padding: 2.65rem;
        border-radius: 32px;
        color: #f8fbff;
        background:
            radial-gradient(circle at 74% 18%, rgba(118, 228, 197, .34), transparent 17rem),
            radial-gradient(circle at 92% 85%, rgba(23, 182, 214, .28), transparent 15rem),
            linear-gradient(135deg, #07111f 0%, #0a2b55 54%, #0d64d8 100%);
        box-shadow: 0 28px 70px rgba(7, 17, 31, .22);
    }
    .st-key-home-hero [data-testid="stHorizontalBlock"] {
        min-height: 25.7rem;
        align-items: center;
    }
    .klima-home-hero-copy {
        position: relative;
        z-index: 2;
        align-self: center;
    }
    .st-key-home-hero h1 {
        max-width: 48rem;
        margin: .7rem 0 1rem;
        color: #f8fbff;
        font-size: clamp(2.7rem, 5.2vw, 5.25rem);
        line-height: .95;
    }
    .st-key-home-hero h1 span {
        color: #9ff4df;
        font-family: inherit;
    }
    .st-key-home-hero p {
        max-width: 47rem;
        color: rgba(248, 251, 255, .88);
        font-size: 1.04rem;
        line-height: 1.6;
    }
    .klima-home-greeting {
        display: block;
        margin-top: 1rem;
        color: #c8f7ff;
        font-weight: 700;
    }
    .st-key-home-hero .klima-stat-strip {
        max-width: 47rem;
        margin-top: 1.35rem;
    }
    .st-key-open-research-dashboard {
        margin-bottom: .8rem;
    }
    .st-key-open-research-dashboard button {
        min-height: 3.65rem;
        border: 1px solid rgba(255, 255, 255, .78) !important;
        background: linear-gradient(135deg, #ffb020 0%, #f97316 55%, #ea580c 100%) !important;
        box-shadow:
            0 16px 34px rgba(234, 88, 12, .34),
            0 0 0 4px rgba(249, 115, 22, .14) !important;
        color: #ffffff !important;
        font-size: 1rem !important;
        letter-spacing: .01em !important;
        transition: transform .16s ease, box-shadow .16s ease, filter .16s ease !important;
    }
    .st-key-open-research-dashboard button:hover {
        box-shadow:
            0 20px 42px rgba(234, 88, 12, .42),
            0 0 0 5px rgba(249, 115, 22, .20) !important;
        filter: brightness(1.05);
        transform: translateY(-2px);
    }
    .st-key-open-research-dashboard button:focus-visible {
        outline: 3px solid rgba(255, 255, 255, .92);
        outline-offset: 3px;
    }
    .st-key-open-research-dashboard button * {
        color: #ffffff !important;
        font-weight: 800 !important;
    }
    .klima-home-visual {
        position: relative;
        min-height: 20.55rem;
        border: 1px solid rgba(255, 255, 255, .16);
        border-radius: 28px;
        background: rgba(255, 255, 255, .07);
        box-shadow: inset 0 1px 0 rgba(255, 255, 255, .10);
        backdrop-filter: blur(8px);
    }
    .klima-home-visual svg {
        position: absolute;
        inset: 1rem;
        width: calc(100% - 2rem);
        height: calc(100% - 2rem);
    }
    .klima-home-chart-line {
        animation: klima-draw-chart 3.8s ease-in-out infinite alternate;
        stroke-dasharray: 330;
        stroke-dashoffset: 330;
    }
    .klima-home-sun {
        animation: klima-float 4s ease-in-out infinite;
        transform-origin: center;
    }
    .klima-home-cloud {
        animation: klima-cloud 7s ease-in-out infinite alternate;
    }
    .klima-home-station-light {
        animation: klima-pulse 1.8s ease-in-out infinite;
        transform-origin: center;
    }
    .klima-float-label {
        position: absolute;
        z-index: 2;
        padding: .46rem .72rem;
        border: 1px solid rgba(255, 255, 255, .22);
        border-radius: 999px;
        background: rgba(7, 17, 31, .48);
        color: #e7fbff;
        font-size: .76rem;
        font-weight: 700;
        letter-spacing: .03em;
        backdrop-filter: blur(8px);
    }
    .klima-label-temp { top: 1.25rem; right: 1.25rem; }
    .klima-label-chart { bottom: 1.25rem; left: 1.25rem; }
    .klima-label-stations { bottom: 4.65rem; right: 1.25rem; }
    .klima-home-section-lead {
        max-width: 54rem;
        margin: -.25rem 0 1rem;
        color: #39536f;
        line-height: 1.55;
    }
    .klima-data-grid,
    .klima-flow-grid {
        display: grid;
        gap: 1rem;
    }
    .klima-data-grid {
        grid-template-columns: repeat(4, minmax(0, 1fr));
        margin: .8rem 0 1.6rem;
    }
    .klima-data-card,
    .klima-flow-card,
    .klima-analysis-card {
        border: 1px solid rgba(13, 100, 216, .13);
        border-radius: 22px;
        background: rgba(255, 255, 255, .88);
        box-shadow: 0 16px 38px rgba(7, 17, 31, .08);
    }
    .klima-data-card {
        min-height: 9rem;
        padding: 1.15rem;
    }
    .klima-data-card strong {
        display: block;
        color: #0d64d8;
        font-family: 'Manrope', sans-serif;
        font-size: 2rem;
        line-height: 1;
    }
    .klima-data-card span {
        display: block;
        margin-top: .5rem;
        color: #07111f;
        font-weight: 800;
    }
    .klima-data-card p,
    .klima-flow-card p,
    .klima-analysis-card p {
        margin-bottom: 0;
        color: #45617d;
        line-height: 1.5;
    }
    .klima-flow-grid {
        grid-template-columns: repeat(4, minmax(0, 1fr));
        margin: .8rem 0 1.5rem;
    }
    .klima-flow-card {
        position: relative;
        min-height: 11rem;
        padding: 1.15rem;
        overflow: hidden;
    }
    .klima-flow-step {
        display: inline-grid;
        width: 2.15rem;
        height: 2.15rem;
        place-items: center;
        border-radius: 50%;
        background: linear-gradient(135deg, #ffb020, #f97316);
        color: #ffffff;
        font-weight: 800;
        box-shadow: 0 8px 18px rgba(249, 115, 22, .24);
    }
    .klima-flow-card h3 {
        margin: .8rem 0 .35rem;
        font-size: 1.04rem;
    }
    .klima-analysis-card {
        margin: .8rem 0 1.35rem;
        padding: 1.35rem;
        overflow: hidden;
    }
    .klima-analysis-intro {
        display: grid;
        grid-template-columns: minmax(0, 1.16fr) minmax(18rem, .84fr);
        gap: 1rem;
        align-items: center;
    }
    .klima-analysis-list {
        display: flex;
        flex-wrap: wrap;
        gap: .5rem;
        margin-top: .9rem;
    }
    .klima-analysis-list span {
        padding: .36rem .62rem;
        border-radius: 999px;
        background: #e8f3ff;
        color: #0a4b9e;
        font-size: .8rem;
        font-weight: 700;
    }
    .klima-basics-grid,
    .klima-tools-grid {
        display: grid;
        gap: .75rem;
        margin-top: 1rem;
    }
    .klima-basics-grid {
        grid-template-columns: repeat(3, minmax(0, 1fr));
    }
    .klima-tools-grid {
        grid-template-columns: repeat(3, minmax(0, 1fr));
    }
    .klima-basics-item,
    .klima-tool-item {
        padding: .9rem;
        border-radius: 16px;
        background: rgba(232, 243, 255, .66);
        border: 1px solid rgba(13, 100, 216, .10);
    }
    .klima-basics-item strong,
    .klima-tool-item strong {
        display: block;
        margin-bottom: .28rem;
        color: #0a4b9e;
        font-family: 'Manrope', sans-serif;
        font-size: .92rem;
    }
    .klima-basics-item p,
    .klima-tool-item p {
        color: #45617d;
        font-size: .88rem;
        line-height: 1.45;
    }
    .klima-tools-title {
        margin: 1.2rem 0 0;
        color: #07111f;
        font-size: 1rem;
    }
    .klima-mini-chart {
        align-self: center;
        min-height: 13rem;
        padding: .85rem;
        border-radius: 18px;
        background:
            linear-gradient(rgba(13, 100, 216, .08) 1px, transparent 1px),
            linear-gradient(90deg, rgba(13, 100, 216, .08) 1px, transparent 1px),
            linear-gradient(135deg, rgba(219, 234, 254, .75), rgba(240, 253, 250, .86));
        background-size: 28px 28px, 28px 28px, auto;
    }
    .klima-mini-chart svg {
        width: 100%;
        height: 100%;
    }
    .klima-mini-wave {
        animation: klima-draw-chart 4.2s ease-in-out infinite alternate;
        stroke-dasharray: 430;
        stroke-dashoffset: 430;
    }
    .klima-home-note {
        margin: .65rem 0 0;
        color: #56718d;
        font-size: .9rem;
    }
    @keyframes klima-draw-chart {
        to { stroke-dashoffset: 0; }
    }
    @keyframes klima-float {
        0%, 100% { transform: translateY(0) rotate(0); }
        50% { transform: translateY(-8px) rotate(6deg); }
    }
    @keyframes klima-cloud {
        from { transform: translateX(-8px); }
        to { transform: translateX(9px); }
    }
    @keyframes klima-pulse {
        0%, 100% { opacity: .72; transform: scale(.86); }
        50% { opacity: 1; transform: scale(1.16); }
    }
    @media (prefers-reduced-motion: reduce) {
        .klima-home-chart-line,
        .klima-home-sun,
        .klima-home-cloud,
        .klima-home-station-light,
        .klima-mini-wave {
            animation: none !important;
            stroke-dashoffset: 0 !important;
        }
    }
    @media (max-width: 900px) {
        .klima-analysis-intro {
            grid-template-columns: 1fr;
        }
        .klima-basics-grid,
        .klima-tools-grid {
            grid-template-columns: repeat(2, minmax(0, 1fr));
        }
        .klima-home-visual {
            min-height: 18rem;
        }
        .klima-data-grid,
        .klima-flow-grid {
            grid-template-columns: repeat(2, minmax(0, 1fr));
        }
    }
    @media (max-width: 560px) {
        .st-key-home-hero { padding: 1.35rem; }
        .klima-data-grid,
        .klima-flow-grid,
        .klima-basics-grid,
        .klima-tools-grid {
            grid-template-columns: 1fr;
        }
    }
    </style>
    """,
    unsafe_allow_html=True,
)

with st.container(key="home-hero"):
    hero_copy, hero_visual = st.columns([1.22, 0.78], gap="small", vertical_alignment="center")
    with hero_copy:
        st.markdown(
            f"""
        <div class="klima-home-hero-copy">
            <span class="klima-kicker">Пространство климатической аналитики</span>
            <h1>Исследуйте климат <span>по данным метеостанций</span></h1>
            <p>
                «КлиматикА» собирает в одном интерфейсе карту станций, временные ряды,
                сравнения, климатограммы, корреляции, исследовательский прогноз и PDF-отчёты.
                Клиент помогает выбрать контекст, а расчёты выполняет backend API.
            </p>
            <span class="klima-home-greeting">Рабочая сессия: {display_name}</span>
            <div class="klima-stat-strip">
                <div class="klima-stat"><strong>{hero_station_value}</strong><span>метеостанций в справочнике</span></div>
                <div class="klima-stat"><strong>8</strong><span>рабочих сценариев анализа</span></div>
                <div class="klima-stat"><strong>{hero_period_value}</strong><span>{hero_period_caption}</span></div>
            </div>
        </div>
        """,
            unsafe_allow_html=True,
        )
    with hero_visual:
        if st.button(
            "🔬 Открыть исследовательскую панель",
            type="primary",
            key="open-research-dashboard",
            width="stretch",
        ):
            st.switch_page("pages/00_Dashboard.py")
        st.markdown(
            """
            <div class="klima-home-visual" aria-label="Минималистичная иллюстрация климатического мониторинга">
                <span class="klima-float-label klima-label-temp">Температура</span>
                <span class="klima-float-label klima-label-stations">Метеостанции</span>
                <span class="klima-float-label klima-label-chart">Месячные ряды</span>
                <svg viewBox="0 0 360 360" role="img" aria-label="Метеостанция и график климатических данных">
                    <g class="klima-home-sun" fill="none" stroke="#ffd166" stroke-linecap="round" stroke-width="5">
                        <circle cx="284" cy="74" r="25" fill="rgba(255, 209, 102, .2)"/>
                        <path d="M284 27v17M284 104v17M237 74h17M314 74h17M251 41l12 12M305 95l12 12M317 41l-12 12M263 95l-12 12"/>
                    </g>
                    <g class="klima-home-cloud" fill="rgba(255,255,255,.12)" stroke="#c8f7ff" stroke-width="4">
                        <path d="M43 96c0-14 11-25 25-25 4 0 8 1 11 3 7-14 21-23 37-23 22 0 40 17 42 39 14 1 25 12 25 26 0 14-12 26-26 26H69c-14 0-26-11-26-26 0-7 3-14 8-18-5-1-8-2-8-2Z"/>
                    </g>
                    <g fill="none" stroke="#9ff4df" stroke-linecap="round" stroke-linejoin="round" stroke-width="6">
                        <path d="M86 281h116"/>
                        <path d="M143 281V149"/>
                        <path d="M117 281l26-132 27 132"/>
                        <path d="M121 225h44M127 194h32M134 164h18"/>
                        <path d="M143 149l34-20"/>
                        <circle class="klima-home-station-light" cx="179" cy="128" r="7" fill="#ffb020" stroke="#ffd166"/>
                        <path d="M143 126v23M117 281h-17M170 281h17"/>
                    </g>
                    <g fill="none" stroke-linecap="round" stroke-linejoin="round">
                        <path d="M32 313H330" stroke="rgba(255,255,255,.28)" stroke-width="2"/>
                        <path class="klima-home-chart-line" d="M35 292c23-9 31-22 47-17 20 6 26 18 45 8 20-11 29-45 49-39 20 5 26 39 47 31 22-9 28-55 49-50 18 4 22 35 40 26 14-6 20-23 36-28" stroke="#ffb020" stroke-width="7"/>
                    </g>
                </svg>
            </div>
            """,
            unsafe_allow_html=True,
        )

st.subheader("Как проходит исследование")
st.markdown(
    """
    <p class="klima-home-section-lead">
        Начните с исследовательской панели: она хранит единый контекст и передаёт его
        аналитическим страницам. Так разные сценарии можно запускать последовательно,
        не собирая выбор заново.
    </p>
    <div class="klima-flow-grid">
        <div class="klima-flow-card">
            <span class="klima-flow-step">1</span>
            <h3>Выберите станции</h3>
            <p>Найдите точки на карте, настройте отображение и сформируйте географическую выборку.</p>
        </div>
        <div class="klima-flow-card">
            <span class="klima-flow-step">2</span>
            <h3>Задайте климатический срез</h3>
            <p>Укажите период и агрегацию: исходные значения станут общим контекстом анализа.</p>
        </div>
        <div class="klima-flow-card">
            <span class="klima-flow-step">3</span>
            <h3>Запустите сценарий</h3>
            <p>Исследуйте ряды, периоды, станции, климатограммы, связи между параметрами и прогноз.</p>
        </div>
        <div class="klima-flow-card">
            <span class="klima-flow-step">4</span>
            <h3>Сохраните результат</h3>
            <p>Вернитесь к истории запусков, сохраните набор анализа или сформируйте PDF-отчёт.</p>
        </div>
    </div>
    """,
    unsafe_allow_html=True,
)

st.subheader("Базовый климатический анализ")
st.markdown(
    """
    <div class="klima-analysis-card">
        <div class="klima-analysis-intro">
            <div>
                <h3>От измерений станции к климатическому выводу</h3>
                <p>
                    Метеостанция — это точка наблюдений с координатами и временными рядами показателей.
                    Одно значение описывает погоду в конкретный момент, а климатический вывод появляется
                    при анализе повторяющихся наблюдений за выбранный период. Поэтому важно сравнивать
                    сопоставимые станции, учитывать их расположение и смотреть не только на отдельные
                    экстремумы, но и на устойчивую картину.
                </p>
                <div class="klima-analysis-list">
                    <span>температура</span>
                    <span>осадки</span>
                    <span>влажность</span>
                    <span>давление</span>
                </div>
            </div>
            <div class="klima-mini-chart" aria-label="Схематичный график сезонного климатического ряда">
                <svg viewBox="0 0 430 190" role="img" aria-label="Сезонный климатический ряд с линией тренда">
                    <path d="M22 151H408" stroke="#9ab4d0" stroke-width="2"/>
                    <path d="M22 104H408M22 57H408" stroke="#bdd2e6" stroke-dasharray="5 7" stroke-width="2"/>
                    <path d="M25 124L405 79" stroke="#f97316" stroke-dasharray="8 8" stroke-width="4"/>
                    <path class="klima-mini-wave" d="M25 132c21 0 24-61 48-61s27 83 51 83 27-88 52-88 27 70 52 70 27-90 52-90 27 79 52 79 29-69 73-73" fill="none" stroke="#0d64d8" stroke-linecap="round" stroke-width="7"/>
                    <circle cx="280" cy="46" r="8" fill="#ffb020"/>
                </svg>
            </div>
        </div>
        <div class="klima-basics-grid">
            <div class="klima-basics-item">
                <strong>Период</strong>
                <p>Определяет, какой отрезок истории изучается. Для климатических выводов важен достаточно длинный и сопоставимый интервал.</p>
            </div>
            <div class="klima-basics-item">
                <strong>Агрегация</strong>
                <p>Объединяет наблюдения по месяцам или годам. Это уменьшает шум и помогает увидеть сезонность и долгосрочные изменения.</p>
            </div>
            <div class="klima-basics-item">
                <strong>Климатическая норма</strong>
                <p>Даёт ориентир для сравнения. Отклонение от типичного уровня помогает заметить аномальные периоды.</p>
            </div>
        </div>
        <h3 class="klima-tools-title">Основные возможности: что использовать и зачем</h3>
        <div class="klima-tools-grid">
            <div class="klima-tool-item">
                <strong>Временной ряд</strong>
                <p>Показывает динамику показателя, тренд, скользящее среднее, аномалии и экстремумы для одной станции.</p>
            </div>
            <div class="klima-tool-item">
                <strong>Сравнение периодов</strong>
                <p>Нужно, когда важно понять, как изменился показатель между интервалами: например, между десятилетиями.</p>
            </div>
            <div class="klima-tool-item">
                <strong>Сравнение станций</strong>
                <p>Помогает увидеть географические различия одного показателя и сопоставить выбранные точки на карте.</p>
            </div>
            <div class="klima-tool-item">
                <strong>Климатограмма</strong>
                <p>Показывает годовой ритм температуры и осадков по месяцам. Удобна для быстрого сравнения сезонов.</p>
            </div>
            <div class="klima-tool-item">
                <strong>Корреляции</strong>
                <p>Показывают, как совместно меняются параметры одной станции. Связь помогает искать гипотезы, но сама по себе не доказывает причину.</p>
            </div>
            <div class="klima-tool-item">
                <strong>Прогноз и отчёт</strong>
                <p>Прогноз даёт исследовательскую оценку будущей динамики, а PDF-отчёт собирает выбранные результаты для сохранения.</p>
            </div>
        </div>
    </div>
    """,
    unsafe_allow_html=True,
)

if dataset:
    st.subheader("Что доступно в локальном demo-наборе")
    st.markdown(
        f"""
        <p class="klima-home-section-lead">
            Sample-режим подходит для знакомства с интерфейсом без запущенного backend.
            Он сочетает справочник станций, реальные месячные ряды и детерминированные demo-данные
            для проверки аналитических сценариев.
        </p>
        <div class="klima-data-grid">
            <div class="klima-data-card">
                <strong>{dataset["stations"]}</strong>
                <span>метеостанций</span>
                <p>Локальный SQLite-справочник с координатами, странами и регионами.</p>
            </div>
            <div class="klima-data-card">
                <strong>{dataset["countries"]}</strong>
                <span>стран в справочнике</span>
                <p>Карта помогает собрать географический срез перед анализом.</p>
            </div>
            <div class="klima-data-card">
                <strong>{dataset["parameters"]}</strong>
                <span>климатических показателя</span>
                <p>Температура, осадки, влажность и атмосферное давление.</p>
            </div>
            <div class="klima-data-card">
                <strong>{dataset["real_stations"]}</strong>
                <span>арктических станций</span>
                <p>Реальные месячные ряды Meteostat за {dataset["period"]} годы.</p>
            </div>
        </div>
        <p class="klima-home-note">
            В рабочем backend-режиме состав справочников и доступный период определяются ответами API.
        </p>
        """,
        unsafe_allow_html=True,
    )
else:
    st.info("Справочники метеостанций, показателей и доступные периоды загружаются из подключённого backend API.")
