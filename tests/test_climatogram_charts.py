from __future__ import annotations

from app.components.charts import (
    _closed_month_trace,
    climatogram_axis_options,
    climatogram_records_dataframe,
    climatogram_scatter_dataframe,
)


def _items(months: list[dict]) -> list[dict]:
    """Создаёт тестовые результаты климатограммы.

    Args:
        months: Месячные записи результата.

    Returns:
        Список элементов климатограммы в формате страницы.
    """

    return [
        {
            "station_id": 1,
            "station_name": "Тестовая станция",
            "period_index": 0,
            "period_label": "Базовый период",
            "result": {"months": months},
        }
    ]


def test_climatogram_records_dataframe_accepts_current_fields() -> None:
    """Проверяет нормализацию текущих полей sample/backend климатограммы.

    Returns:
        None.
    """

    df = climatogram_records_dataframe(
        _items([{"month": 1, "temperature_mean": -12.5, "precipitation_sum": 18.0}])
    )

    assert df.iloc[0]["temperature_mean"] == -12.5
    assert df.iloc[0]["precipitation_sum"] == 18.0
    assert df.iloc[0]["month_label"] == "Янв"
    assert df.iloc[0]["month_sequence_label"] == "01 Янв"


def test_climatogram_records_dataframe_accepts_norm_fields() -> None:
    """Проверяет fallback на поля норм за период 1995-2024.

    Returns:
        None.
    """

    df = climatogram_records_dataframe(
        _items([{"month": 2, "tavg_norm_1995_2024": -9.25, "prcp_norm_1995_2024": 21.4}])
    )

    assert df.iloc[0]["temperature_mean"] == -9.25
    assert df.iloc[0]["precipitation_sum"] == 21.4
    assert df.iloc[0]["tavg_norm_1995_2024"] == -9.25
    assert df.iloc[0]["prcp_norm_1995_2024"] == 21.4


def test_climatogram_axis_options_include_extra_numeric_fields() -> None:
    """Проверяет добавление дополнительных числовых полей в список осей.

    Returns:
        None.
    """

    options = dict(
        climatogram_axis_options(
            _items(
                [
                    {
                        "month": 3,
                        "temperature_mean": -5.0,
                        "precipitation_sum": 15.0,
                        "humidity_index": 0.72,
                    }
                ]
            )
        )
    )

    assert options["temperature_mean"] == "Температура, °C"
    assert options["precipitation_sum"] == "Осадки, мм"
    assert options["humidity_index"] == "humidity_index"


def test_climatogram_scatter_dataframe_drops_rows_without_selected_axes() -> None:
    """Проверяет отбрасывание строк без выбранных X/Y значений.

    Returns:
        None.
    """

    df = climatogram_scatter_dataframe(
        _items(
            [
                {"month": 1, "temperature_mean": -10.0, "precipitation_sum": 10.0},
                {"month": 2, "temperature_mean": None, "precipitation_sum": 12.0},
                {"month": 3, "temperature_mean": -3.0, "precipitation_sum": None},
            ]
        ),
        "temperature_mean",
        "precipitation_sum",
    )

    assert len(df) == 1
    assert df.iloc[0]["month"] == 1


def test_closed_month_trace_adds_january_after_december() -> None:
    """Проверяет замыкание годового хода в многоугольник.

    Returns:
        None.
    """

    df = climatogram_scatter_dataframe(
        _items(
            [
                {"month": month, "temperature_mean": float(month), "precipitation_sum": float(month * 10)}
                for month in range(1, 13)
            ]
        ),
        "temperature_mean",
        "precipitation_sum",
    )
    closed = _closed_month_trace(df)

    assert len(closed) == 13
    assert closed.iloc[0]["month_order"] == 1
    assert closed.iloc[-1]["month_order"] == 1
