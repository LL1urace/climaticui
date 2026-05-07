from __future__ import annotations

from datetime import date

from klimatika_frontend.utils.validators import periods_overlap, validate_min_stations, validate_period, validate_required_filters


def test_validate_period_rejects_reversed_dates() -> None:
    result = validate_period(date(2021, 1, 1), date(2020, 1, 1))
    assert result.ok is False


def test_validate_required_filters_requires_station_and_parameter() -> None:
    result = validate_required_filters(None, 1, date(2020, 1, 1), date(2020, 2, 1))
    assert result.ok is False
    assert "метеостанцию" in result.message


def test_validate_min_stations() -> None:
    assert validate_min_stations([1]).ok is False
    assert validate_min_stations([1, 2]).ok is True


def test_periods_overlap() -> None:
    assert periods_overlap(date(2020, 1, 1), date(2020, 2, 1), date(2020, 1, 15), date(2020, 3, 1))
    assert not periods_overlap(date(2020, 1, 1), date(2020, 2, 1), date(2020, 2, 2), date(2020, 3, 1))
