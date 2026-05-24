"""Validation helpers for form inputs."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Any


@dataclass(frozen=True)
class ValidationResult:
    """Описывает результат проверки пользовательского ввода.

    Attributes:
        ok: Флаг успешной валидации.
        message: Сообщение об ошибке или пустая строка.
    """

    ok: bool
    message: str = ""


def validate_period(date_from: date | None, date_to: date | None) -> ValidationResult:
    """Проверяет корректность выбранного периода дат.

    Args:
        date_from: Начальная дата периода.
        date_to: Конечная дата периода.

    Returns:
        Результат валидации периода.
    """

    if not date_from or not date_to:
        return ValidationResult(False, "Выберите начало и конец периода.")
    if date_from > date_to:
        return ValidationResult(False, "Дата начала периода не может быть позже даты окончания.")
    return ValidationResult(True)


def validate_required_filters(station_id: Any, parameter_id: Any, date_from: date | None, date_to: date | None) -> ValidationResult:
    """Проверяет обязательные фильтры станции, параметра и периода.

    Args:
        station_id: Идентификатор выбранной станции.
        parameter_id: Идентификатор выбранного параметра.
        date_from: Начальная дата периода.
        date_to: Конечная дата периода.

    Returns:
        Результат валидации обязательных фильтров.
    """

    if not station_id:
        return ValidationResult(False, "Выберите метеостанцию.")
    if not parameter_id:
        return ValidationResult(False, "Выберите климатический параметр.")
    return validate_period(date_from, date_to)


def validate_min_stations(station_ids: list[Any], min_count: int = 2) -> ValidationResult:
    """Проверяет минимальное количество выбранных станций.

    Args:
        station_ids: Список идентификаторов выбранных станций.
        min_count: Минимально допустимое количество станций.

    Returns:
        Результат валидации количества станций.
    """

    if len(station_ids) < min_count:
        return ValidationResult(False, f"Выберите минимум {min_count} станции.")
    return ValidationResult(True)


def periods_overlap(first_start: date, first_end: date, second_start: date, second_end: date) -> bool:
    """Проверяет пересечение двух периодов дат.

    Args:
        first_start: Начало первого периода.
        first_end: Конец первого периода.
        second_start: Начало второго периода.
        second_end: Конец второго периода.

    Returns:
        True, если периоды пересекаются.
    """

    return max(first_start, second_start) <= min(first_end, second_end)

