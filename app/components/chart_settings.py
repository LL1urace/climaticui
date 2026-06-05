"""Общие настройки внешнего вида интерактивных графиков."""

from __future__ import annotations

from typing import Any

import streamlit as st


DEFAULT_CHART_STYLE = {
    "chart_primary_color": "#0d64d8",
    "chart_accent_color": "#f59e0b",
    "chart_negative_color": "#07111f",
    "chart_bar_color": "#17b6d6",
    "chart_line_dash": "solid",
    "chart_line_width": 3.0,
    "chart_show_markers": True,
    "chart_marker_size": 7,
    "chart_bar_opacity": 0.72,
    "chart_template": "plotly_white",
    "chart_vary_series_dashes": True,
}
ACTIVE_CHART_SCOPE_KEY = "chart_active_scope"

LINE_DASH_LABELS = {
    "solid": "Сплошная",
    "dash": "Пунктир",
    "dot": "Точки",
    "dashdot": "Штрих-точка",
    "longdash": "Длинный пунктир",
}
TEMPLATE_LABELS = {
    "plotly_white": "Светлая",
    "simple_white": "Минималистичная",
    "plotly": "Стандартная",
}


def _safe_session_value(key: str, default: Any) -> Any:
    """Возвращает значение session_state с fallback для неинтерактивных проверок."""

    try:
        return st.session_state.get(key, default)
    except Exception:
        return default


def _scoped_key(scope: str | None, key: str) -> str:
    """Формирует ключ session_state для конкретной страницы."""

    return f"{scope}_{key}" if scope else key


def set_active_chart_scope(scope: str) -> None:
    """Запоминает, настройки какой страницы должны применяться к графикам."""

    st.session_state[ACTIVE_CHART_SCOPE_KEY] = scope


def ensure_chart_style_defaults(scope: str | None = None) -> None:
    """Инициализирует ключи стиля графиков до создания sidebar-виджетов."""

    for key, value in DEFAULT_CHART_STYLE.items():
        scoped_key = _scoped_key(scope, key)
        if scoped_key not in st.session_state:
            st.session_state[scoped_key] = st.session_state.get(key, value)
    if st.session_state.get(_scoped_key(scope, "chart_line_dash")) not in LINE_DASH_LABELS:
        st.session_state[_scoped_key(scope, "chart_line_dash")] = DEFAULT_CHART_STYLE["chart_line_dash"]
    if st.session_state.get(_scoped_key(scope, "chart_template")) not in TEMPLATE_LABELS:
        st.session_state[_scoped_key(scope, "chart_template")] = DEFAULT_CHART_STYLE["chart_template"]


def get_chart_style(scope: str | None = None) -> dict[str, Any]:
    """Возвращает текущий стиль графиков, выбранный в sidebar."""

    active_scope = scope or _safe_session_value(ACTIVE_CHART_SCOPE_KEY, None)
    return {
        key: _safe_session_value(_scoped_key(active_scope, key), _safe_session_value(key, default))
        for key, default in DEFAULT_CHART_STYLE.items()
    }


def render_chart_visual_controls(
    scope: str,
    title: str,
    caption: str,
    controls: tuple[str, ...] = ("line", "bar", "negative", "template"),
    expanded: bool = False,
) -> None:
    """Отображает настройки внешнего вида графиков для конкретной страницы."""

    set_active_chart_scope(scope)
    ensure_chart_style_defaults(scope)
    control_set = set(controls)
    rendered_fields: set[str] = set()

    def color_control(field: str, label: str) -> None:
        if field in rendered_fields:
            return
        rendered_fields.add(field)
        st.color_picker(label, key=_scoped_key(scope, field))

    with st.expander(title, expanded=expanded):
        st.caption(caption)
        if "line" in control_set or "scatter" in control_set:
            color_control("chart_primary_color", "Цвет линий и точек")
        if "line" in control_set or "heatmap" in control_set:
            color_control("chart_accent_color", "Акцентный цвет")
        if "negative" in control_set or "heatmap" in control_set:
            color_control("chart_negative_color", "Цвет отрицательных значений")
        if "bar" in control_set:
            color_control("chart_bar_color", "Цвет столбцов")

        if "line" in control_set:
            st.selectbox(
                "Тип линии",
                options=list(LINE_DASH_LABELS),
                format_func=lambda item: LINE_DASH_LABELS[item],
                key=_scoped_key(scope, "chart_line_dash"),
            )
            st.slider(
                "Толщина линии",
                min_value=1.0,
                max_value=6.0,
                step=0.5,
                key=_scoped_key(scope, "chart_line_width"),
            )
            st.checkbox("Показывать точки на линиях", key=_scoped_key(scope, "chart_show_markers"))
            st.checkbox("Разные штрихи для серий", key=_scoped_key(scope, "chart_vary_series_dashes"))

        if "line" in control_set or "scatter" in control_set:
            st.slider("Размер точек", min_value=4, max_value=16, step=1, key=_scoped_key(scope, "chart_marker_size"))

        if "bar" in control_set:
            st.slider(
                "Прозрачность столбцов",
                min_value=0.25,
                max_value=1.0,
                step=0.01,
                key=_scoped_key(scope, "chart_bar_opacity"),
            )

        if "template" in control_set:
            st.selectbox(
                "Тема графиков",
                options=list(TEMPLATE_LABELS),
                format_func=lambda item: TEMPLATE_LABELS[item],
                key=_scoped_key(scope, "chart_template"),
            )
