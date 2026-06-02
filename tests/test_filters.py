from __future__ import annotations

from datetime import date

from app.components import filters
from app.components.filters import availability_details_message, availability_period_message, availability_ranges_message
from app.state.session import PERSISTED_FORM_VALUES_KEY


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


def test_parameter_forms_start_without_assumed_station_parameter_or_dates(monkeypatch) -> None:
    """Проверяет пустое начальное состояние обязательных пользовательских полей."""

    state: dict = {}
    selectbox_calls: list[dict] = []
    date_calls: list[dict] = []

    def fake_selectbox(_label: str, **kwargs):
        selectbox_calls.append(kwargs)
        return None

    def fake_date_input(_label: str, **kwargs):
        date_calls.append(kwargs)
        return kwargs["value"]

    monkeypatch.setattr(filters.st, "session_state", state)
    monkeypatch.setattr(filters.st, "selectbox", fake_selectbox)
    monkeypatch.setattr(filters.st, "date_input", fake_date_input)

    stations = [{"id": 1, "name": "Station 1"}]
    parameters = [{"id": 1, "name": "Temperature"}]

    assert filters.select_station(stations, key="analysis_station") is None
    assert filters.select_parameter(parameters, key="analysis_parameter") is None
    assert filters.date_period("analysis") == (None, None)
    assert selectbox_calls[0]["index"] is None
    assert selectbox_calls[1]["index"] is None
    assert [call["value"] for call in date_calls] == [None, None]


def test_common_context_is_restored_on_another_page_after_widget_cleanup(monkeypatch) -> None:
    """Проверяет перенос станции и периода между страницами через постоянное состояние."""

    state: dict = {}
    current_dates = [date(2020, 1, 1), date(2024, 12, 31)]

    def fake_selectbox(_label: str, **kwargs):
        if kwargs["key"] == "analysis_station":
            return 2
        index = kwargs["index"]
        return kwargs["options"][index] if index is not None else None

    def fake_date_input(_label: str, **kwargs):
        if kwargs["key"].startswith("analysis_"):
            return current_dates.pop(0)
        return kwargs["value"]

    monkeypatch.setattr(filters.st, "session_state", state)
    monkeypatch.setattr(filters.st, "selectbox", fake_selectbox)
    monkeypatch.setattr(filters.st, "date_input", fake_date_input)

    stations = [{"id": 1, "name": "Station 1"}, {"id": 2, "name": "Station 2"}]

    assert filters.select_station(stations, key="analysis_station") == 2
    assert filters.date_period("analysis") == (date(2020, 1, 1), date(2024, 12, 31))
    state.pop("analysis_station", None)
    state.pop("analysis_date_from", None)
    state.pop("analysis_date_to", None)

    assert filters.select_station(stations, key="forecast_station") == 2
    assert filters.date_period("forecast") == (date(2020, 1, 1), date(2024, 12, 31))
    assert state["selected_station_id"] == 2
    assert state["dashboard_station_ids"] == [2]


def test_clearing_analysis_context_clears_dashboard_context(monkeypatch) -> None:
    """Проверяет очистку общих полей панели со страницы анализа."""

    state: dict = {
        "selected_station_id": 2,
        "selected_parameter_id": 1,
        "dashboard_station_ids": [2],
        "dashboard_date_from": date(2020, 1, 1),
        "dashboard_date_to": date(2024, 12, 31),
    }

    monkeypatch.setattr(filters.st, "session_state", state)
    monkeypatch.setattr(filters.st, "selectbox", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(filters.st, "date_input", lambda *_args, **_kwargs: None)

    stations = [{"id": 1, "name": "Station 1"}, {"id": 2, "name": "Station 2"}]
    parameters = [{"id": 1, "name": "Temperature"}]

    assert filters.select_station(stations, key="analysis_station") is None
    assert filters.select_parameter(parameters, key="analysis_parameter") is None
    assert filters.date_period("analysis") == (None, None)
    assert state["dashboard_station_ids"] == []
    assert state["selected_parameter_id"] is None
    assert state["dashboard_date_from"] is None
    assert state["dashboard_date_to"] is None


def test_shared_widget_callback_updates_dashboard_before_rerender(monkeypatch) -> None:
    """Проверяет фиксацию очистки основного поля до повторной отрисовки."""

    state = {
        "analysis_station": None,
        "analysis_parameter": None,
        "selected_station_id": 2,
        "dashboard_station_ids": [2],
        "selected_parameter_id": 1,
    }
    monkeypatch.setattr(filters.st, "session_state", state)

    filters._remember_shared_widget_value("analysis_station", "selected_station_id")
    filters._remember_shared_widget_value("analysis_parameter", "selected_parameter_id")

    assert state["selected_station_id"] is None
    assert state["dashboard_station_ids"] == []
    assert state["selected_parameter_id"] is None


def test_local_additional_setting_is_restored_after_widget_cleanup(monkeypatch) -> None:
    """Проверяет сохранение дополнительной настройки только для её страницы."""

    state: dict = {}

    def fake_number_input(_label: str, **kwargs):
        return state.get(kwargs["key"], kwargs["value"])

    monkeypatch.setattr(filters.st, "session_state", state)
    monkeypatch.setattr(filters.st, "number_input", fake_number_input)

    state["analysis_ma_window"] = 24
    assert filters.persistent_number_input("Окно", key="analysis_ma_window", default=12) == 24
    state.pop("analysis_ma_window")

    assert filters.persistent_number_input("Окно", key="analysis_ma_window", default=12) == 24
    assert state[PERSISTED_FORM_VALUES_KEY]["analysis_ma_window"] == 24


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
