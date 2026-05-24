from __future__ import annotations

import sys
from datetime import datetime
from pathlib import Path

import streamlit as st

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.components.layout import page_title, render_home_button, setup_page
from app.components.sidebar import render_sidebar
from app.reports.pdf import build_pdf_report
from app.reports.sections import ReportSection, collect_report_sections
from app.state.session import init_session_state, require_auth


def _selected_sections(sections: list[ReportSection]) -> list[ReportSection]:
    """Отображает чекбоксы выбора разделов PDF-отчёта.

    Args:
        sections: Все разделы отчёта с флагами доступности.

    Returns:
        Список выбранных доступных разделов.
    """

    stored_selection = st.session_state.get("report_selected_sections")
    selected_ids: list[str] = []
    st.markdown("### Разделы отчёта")
    for section in sections:
        default_value = section.available and (
            section.id in stored_selection if isinstance(stored_selection, list) else True
        )
        value = st.checkbox(
            section.title,
            value=default_value,
            key=f"report_section_{section.id}",
            disabled=not section.available,
            help=section.reason or section.description,
        )
        st.caption(section.description if section.available else f"Недоступно: {section.reason}")
        if value and section.available:
            selected_ids.append(section.id)
    st.session_state["report_selected_sections"] = selected_ids
    return [section for section in sections if section.id in selected_ids]


def _render_report_settings() -> tuple[bool, bool, bool]:
    """Отображает настройки содержимого PDF.

    Returns:
        Кортеж флагов: титульная страница, графики, таблицы.
    """

    st.markdown("### Настройки")
    include_cover = st.checkbox(
        "Включать титульную страницу",
        value=bool(st.session_state.get("report_include_cover", True)),
        key="report_include_cover",
    )
    include_graphs = st.checkbox(
        "Включать графики",
        value=bool(st.session_state.get("report_include_graphs", True)),
        key="report_include_graphs",
    )
    include_tables = st.checkbox(
        "Включать таблицы",
        value=bool(st.session_state.get("report_include_tables", True)),
        key="report_include_tables",
    )
    return include_cover, include_graphs, include_tables


setup_page("Отчёты")
init_session_state()
require_auth()
render_sidebar()
page_title("Отчёты", "Соберите PDF из уже рассчитанных результатов приложения.")
render_home_button()

st.info(
    "PDF формируется прямо во frontend из текущей Streamlit-сессии. "
    "Если раздел недоступен, сначала откройте соответствующую страницу и постройте результат. "
    "Для стабильности в один PDF попадёт до 12 графиков; таблицы при этом сохраняются."
)

sections = collect_report_sections(st.session_state)
available_sections = [section for section in sections if section.available]
if not available_sections:
    st.warning("Пока нет данных для отчёта. Запустите анализ, климатограмму, сравнение, прогноз или корреляцию.")

layout_cols = st.columns([0.58, 0.42])
with layout_cols[0]:
    selected_sections = _selected_sections(sections)
with layout_cols[1]:
    include_cover, include_graphs, include_tables = _render_report_settings()
    st.markdown("### Что попадёт в файл")
    if selected_sections:
        for section in selected_sections:
            st.success(section.title)
    else:
        st.caption("Выберите хотя бы один доступный раздел.")

can_build = bool(selected_sections)
if st.button("Сформировать PDF", type="primary", use_container_width=True, disabled=not can_build):
    try:
        with st.spinner("Собираю PDF с графиками и таблицами..."):
            pdf_bytes = build_pdf_report(
                st.session_state,
                selected_sections,
                include_cover=include_cover,
                include_graphs=include_graphs,
                include_tables=include_tables,
                generated_at=datetime.now(),
            )
            st.session_state["last_pdf_report_bytes"] = pdf_bytes
        st.success("PDF сформирован. Можно скачать файл.")
    except Exception as error:
        st.error(f"Не удалось сформировать PDF: {error}")

pdf_bytes = st.session_state.get("last_pdf_report_bytes")
if pdf_bytes:
    st.download_button(
        "Скачать PDF",
        data=pdf_bytes,
        file_name=f"klimatika_report_{datetime.now().strftime('%Y%m%d_%H%M')}.pdf",
        mime="application/pdf",
        use_container_width=True,
    )
