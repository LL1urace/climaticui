from __future__ import annotations

from datetime import date

from app.utils.formatters import format_date, parameter_label, station_label, to_dataframe, unwrap_records


def test_unwrap_records_accepts_list_and_wrapped_items() -> None:
    """Проверяет извлечение записей из списка и вложенных JSON-ключей.

    Returns:
        None.
    """

    assert unwrap_records([{"id": 1}]) == [{"id": 1}]
    assert unwrap_records({"items": [{"id": 2}]}) == [{"id": 2}]
    assert unwrap_records({"data": {"values": [{"id": 3}]}}) == [{"id": 3}]


def test_to_dataframe_from_values() -> None:
    """Проверяет преобразование JSON values в DataFrame.

    Returns:
        None.
    """

    df = to_dataframe({"values": [{"date": "2020-01-01", "value": 1.5}]})
    assert list(df.columns) == ["date", "value"]
    assert df.iloc[0]["value"] == 1.5


def test_station_label_contains_name_code_and_place() -> None:
    """Проверяет формат подписи станции с кодом и регионом.

    Returns:
        None.
    """

    label = station_label({"name": "Moscow", "code": "27612", "country": "RU", "region": "Central"})
    assert label == "Moscow (27612) - RU, Central"


def test_parameter_label_contains_unit() -> None:
    """Проверяет формат подписи параметра с единицей измерения.

    Returns:
        None.
    """

    assert parameter_label({"name": "Temperature", "unit": "°C"}) == "Temperature, °C"


def test_format_date_for_date_object() -> None:
    """Проверяет ISO-форматирование объекта date.

    Returns:
        None.
    """

    assert format_date(date(2020, 1, 2)) == "2020-01-02"

