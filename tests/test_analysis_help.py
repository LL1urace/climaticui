from __future__ import annotations

from app.components.analysis_help import analysis_result_help_entries


def test_analysis_result_help_explains_extreme_outputs() -> None:
    """Проверяет пояснения к показателям экстремумов."""

    entries = dict(analysis_result_help_entries("extremes"))

    assert "Порог p05 (p05)" in entries
    assert "Порог p95 (p95)" in entries
    assert "Низкие экстремумы (low / minima)" in entries
    assert "Высокие экстремумы (high / maxima)" in entries


def test_analysis_result_help_unknown_method_is_empty() -> None:
    """Проверяет, что для неизвестного метода блок не создаётся."""

    assert analysis_result_help_entries("unknown") == []
