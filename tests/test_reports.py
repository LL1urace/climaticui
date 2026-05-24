from __future__ import annotations

import plotly.graph_objects as go

from app.reports.figures import (
    build_climatogram_report_figures,
    build_correlation_heatmap_figure,
    build_station_map_figure,
    build_timeseries_figure,
)
from app.reports.pdf import build_pdf_report
from app.reports import pdf as pdf_module
from app.reports.sections import collect_report_sections


def test_collect_report_sections_marks_available_sections() -> None:
    """Проверяет доступность разделов по fake session state."""

    state = {
        "last_analysis_result": {"results": {"basic_statistics": {"mean": 1.0}}},
        "last_climatogram_items": [{"result": {"months": []}}],
    }

    sections = collect_report_sections(state)
    by_id = {section.id: section for section in sections}

    assert by_id["analysis"].available is True
    assert by_id["climatogram"].available is True
    assert by_id["forecast"].available is False
    assert "Прогнозирование" in by_id["forecast"].page_hint


def test_pdf_builder_returns_pdf_bytes_without_json_preview() -> None:
    """Проверяет, что PDF builder возвращает валидные bytes."""

    state = {
        "last_forecast": {"forecast": [{"date": "2024-01-01", "value": 1.2}]},
        "current_user": {"email": "demo@example.com"},
    }
    selected = [section for section in collect_report_sections(state) if section.available]

    pdf_bytes = build_pdf_report(state, selected, include_graphs=False, include_tables=True)

    assert pdf_bytes.startswith(b"%PDF")
    assert b"json" not in pdf_bytes[:200].lower()


def test_report_figure_builders_return_plotly_figures() -> None:
    """Проверяет основные builders графиков для PDF."""

    timeseries = [{"date": "2024-01-01", "value": 1.0}, {"date": "2024-02-01", "value": 2.0}]
    climatogram_items = [
        {
            "station_id": 1,
            "station_name": "Диксон",
            "period_index": 0,
            "period_label": "1995-2024",
            "result": {
                "months": [
                    {"month": 1, "temperature_mean": -20.0, "precipitation_sum": 22.0},
                    {"month": 2, "temperature_mean": -18.0, "precipitation_sum": 18.0},
                    {"month": 3, "temperature_mean": -14.0, "precipitation_sum": 24.0},
                ]
            },
        }
    ]
    correlation = {
        "labels": ["Температура", "Осадки"],
        "matrix": [[1.0, 0.45], [0.45, 1.0]],
    }
    stations = [{"name": "Диксон", "latitude": 73.5, "longitude": 80.4}]

    assert isinstance(build_timeseries_figure(timeseries), go.Figure)
    assert isinstance(build_correlation_heatmap_figure(correlation), go.Figure)
    assert isinstance(build_station_map_figure(stations), go.Figure)
    figures = build_climatogram_report_figures(
        climatogram_items,
        chart_type="scatter",
        x_axis="temperature_mean",
        y_axis="precipitation_sum",
        connect_months=True,
        close_polygon=True,
        show_labels=True,
        overlay_stations=False,
        overlay_periods=False,
    )
    assert figures
    assert all(isinstance(figure, go.Figure) for figure in figures)


def test_pdf_uses_reportlab_fallback_when_kaleido_fails(monkeypatch) -> None:
    """Проверяет, что график не исчезает при недоступном Kaleido."""

    def fail_export(*_args, **_kwargs) -> bytes:
        raise RuntimeError("kaleido blocked")

    monkeypatch.setattr(pdf_module, "_plotly_figure_png_bytes", fail_export)
    fig = go.Figure(go.Scatter(x=[1, 2, 3], y=[1, 4, 2], mode="lines+markers"))

    flowables = pdf_module._figure_flowables(fig, pdf_module._styles())

    assert any(type(item).__name__ == "Drawing" for item in flowables)
