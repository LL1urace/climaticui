"""Labels and helpers for saved analysis-set scenarios."""

from __future__ import annotations

from typing import Any


SAVE_SET_MODE_LABELS = {
    "dashboard": "Исследовательская панель",
    "analysis": "Анализ временного ряда",
    "period_comparison": "Сравнение периодов",
    "station_comparison": "Сравнение станций",
    "climatogram": "Климатограмма",
    "forecast": "Прогнозирование",
    "correlation": "Корреляционный анализ",
    "report": "Отчёты",
    "reports": "Отчёты",
}

SAVE_SET_MODE_ORDER = (
    "dashboard",
    "analysis",
    "period_comparison",
    "station_comparison",
    "climatogram",
    "forecast",
    "correlation",
    "report",
)


def mode_label(mode: Any) -> str:
    """Returns a user-facing label for a saved-set scenario code."""

    return SAVE_SET_MODE_LABELS.get(str(mode), str(mode))


def normalize_saved_set_modes(value: Any, fallback: Any = None) -> list[str]:
    """Normalizes saved-set mode fields to a unique ordered list of codes."""

    if isinstance(value, dict):
        raw_modes = value.get("modes") or value.get("scenarios") or value.get("mode") or fallback
    else:
        raw_modes = value if value not in (None, "") else fallback

    if raw_modes in (None, ""):
        return []
    if isinstance(raw_modes, (list, tuple, set)):
        candidates = list(raw_modes)
    else:
        candidates = [raw_modes]

    modes = []
    for candidate in candidates:
        if candidate in (None, ""):
            continue
        mode = str(candidate)
        if mode == "reports":
            mode = "report"
        if mode not in modes:
            modes.append(mode)
    return modes


def format_modes(modes: Any) -> str:
    """Formats one or many saved-set scenario codes for tables and captions."""

    normalized_modes = normalize_saved_set_modes(modes)
    return ", ".join(mode_label(mode) for mode in normalized_modes) if normalized_modes else "не задано"
