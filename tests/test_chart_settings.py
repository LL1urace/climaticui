from __future__ import annotations

from app.components import chart_settings


def test_chart_style_uses_active_page_scope(monkeypatch) -> None:
    """Проверяет, что страницы используют независимые настройки графиков."""

    state: dict = {}
    monkeypatch.setattr(chart_settings.st, "session_state", state)

    chart_settings.ensure_chart_style_defaults("analysis")
    chart_settings.ensure_chart_style_defaults("forecast")
    state["analysis_chart_primary_color"] = "#111111"
    state["forecast_chart_primary_color"] = "#222222"

    chart_settings.set_active_chart_scope("analysis")
    assert chart_settings.get_chart_style()["chart_primary_color"] == "#111111"

    chart_settings.set_active_chart_scope("forecast")
    assert chart_settings.get_chart_style()["chart_primary_color"] == "#222222"
