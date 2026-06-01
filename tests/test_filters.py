from __future__ import annotations

from datetime import date

from app.components import filters
from app.components.filters import availability_details_message, availability_period_message, availability_ranges_message


def test_availability_period_message_warns_for_period_without_data() -> None:
    """Проверяет предупреждение для периода вне доступных наблюдений.

    Returns:
        None.
    """

    message = availability_period_message(
        date(2040, 1, 1),
        date(2040, 12, 31),
        "2020-01-01",
        "2024-12-31",
    )

    assert message is not None
    assert message[0] == "warning"
    assert "наблюдений нет" in message[1]


def test_availability_period_message_informs_about_partial_overlap() -> None:
    """Проверяет уведомление для частично доступного периода.

    Returns:
        None.
    """

    message = availability_period_message(
        date(2019, 1, 1),
        date(2020, 12, 31),
        "2020-01-01",
        "2024-12-31",
    )

    assert message is not None
    assert message[0] == "info"
    assert "Часть выбранного периода" in message[1]


def test_availability_period_message_is_empty_for_available_period() -> None:
    """Проверяет отсутствие уведомления для полностью доступного периода.

    Returns:
        None.
    """

    message = availability_period_message(
        date(2021, 1, 1),
        date(2022, 12, 31),
        "2020-01-01",
        "2024-12-31",
    )

    assert message is None


def test_multiselect_stations_uses_session_state_after_map_selection(monkeypatch) -> None:
    """Проверяет синхронизацию очищенного multiselect с выбором станции на карте.

    Args:
        monkeypatch: Фикстура pytest для временной подмены Streamlit.

    Returns:
        None.
    """

    state: dict[str, list[int]] = {}
    calls: list[dict] = []

    def fake_multiselect(_label: str, **kwargs):
        """Имитирует multiselect Streamlit и сохраняет переданные параметры.

        Args:
            _label: Подпись виджета.
            **kwargs: Параметры создания виджета.

        Returns:
            Текущее значение виджета.
        """

        calls.append(kwargs)
        return state.get(kwargs["key"], kwargs.get("default", []))

    monkeypatch.setattr(filters.st, "session_state", state)
    monkeypatch.setattr(filters.st, "multiselect", fake_multiselect)
    stations = [{"id": 1, "name": "Station 1"}, {"id": 2, "name": "Station 2"}]

    assert filters.multiselect_stations(stations, key="dashboard_station_multiselect", default_ids=[1]) == [1]
    assert calls[-1]["default"] == [1]

    state["dashboard_station_multiselect"] = []
    state["dashboard_station_multiselect"] = [2]

    assert filters.multiselect_stations(stations, key="dashboard_station_multiselect", default_ids=[2]) == [2]
    assert "default" not in calls[-1]


def test_availability_ranges_message_warns_when_all_ranges_are_outside_period() -> None:
    """Проверяет предупреждение, если ни один набор данных не покрывает период.

    Returns:
        None.
    """

    message = availability_ranges_message(
        date(2030, 1, 1),
        date(2030, 12, 31),
        [("1995-01-01", "2024-12-31"), ("2000-01-01", "2026-05-01")],
    )

    assert message is not None
    assert message[0] == "warning"
    assert "2026-05-01" in message[1]


def test_availability_ranges_message_informs_when_only_some_ranges_overlap() -> None:
    """Проверяет уведомление, если период доступен только для части наборов.

    Returns:
        None.
    """

    message = availability_ranges_message(
        date(2025, 1, 1),
        date(2025, 12, 31),
        [("1995-01-01", "2024-12-31"), ("2000-01-01", "2026-05-01")],
    )

    assert message is not None
    assert message[0] == "info"


def test_dashboard_availability_uses_api_when_station_metadata_is_empty(monkeypatch) -> None:
    """Проверяет предупреждение панели для станции без диапазонов в справочнике.

    Args:
        monkeypatch: Фикстура pytest для временной подмены API и Streamlit.

    Returns:
        None.
    """

    state: dict = {}
    warnings: list[str] = []

    monkeypatch.setattr(filters.st, "session_state", state)
    monkeypatch.setattr(filters.st, "warning", warnings.append)
    monkeypatch.setattr(
        filters.observations,
        "get_availability",
        lambda station_id, parameter_id: {
            "date_min": "2020-01-01",
            "date_max": "2024-12-31",
            "count": 60,
        },
    )

    filters.render_station_period_availability_notice(
        [{"id": 40953, "name": "Ghaziabad"}],
        date(2030, 1, 1),
        date(2030, 12, 31),
        [1, 2],
    )

    assert len(warnings) == 1
    assert "наблюдений нет" in warnings[0]


def test_availability_details_message_lists_problem_stations_and_parameters() -> None:
    """Проверяет детализацию проблем доступности для нескольких станций.

    Returns:
        None.
    """

    message = availability_details_message(
        date(2025, 1, 1),
        date(2025, 12, 31),
        [
            {
                "station": "Tiksi",
                "parameter": "Температура",
                "date_from": "1995-01-01",
                "date_to": "2024-12-31",
            },
            {
                "station": "Tiksi",
                "parameter": "Осадки",
                "date_from": "1995-01-01",
                "date_to": "2024-12-31",
            },
            {
                "station": "Dikson",
                "parameter": "Температура",
                "date_from": "2025-06-01",
                "date_to": "2026-05-01",
            },
        ],
    )

    assert message is not None
    assert message[0] == "warning"
    assert "**Tiksi**" in message[1]
    assert "Осадки, Температура" in message[1]
    assert "**Dikson**" in message[1]
    assert "период покрыт частично" in message[1]
