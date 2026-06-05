from __future__ import annotations

from datetime import date

from app.state import session


def test_clear_dashboard_context_preserves_auth_cache_and_map_preferences(monkeypatch) -> None:
    """Проверяет точечный сброс аналитического среза панели."""

    state = {
        "access_token": "sample-token",
        "current_user": {"email": "demo@klimatika.local"},
        "is_authenticated": True,
        "cached_stations": [{"id": 1}],
        "selected_station_id": 1,
        "selected_parameter_id": 2,
        "dashboard_station_ids": [1, 2],
        "dashboard_date_from": "2020-01-01",
        "dashboard_date_to": "2024-12-31",
        "dashboard_aggregation": "yearly",
        "dashboard_station_multiselect": [1, 2],
        "dashboard_parameter": 2,
        "dashboard_parameter_ids": [1, 2],
        "dashboard_parameter_3": 2,
        "dashboard_parameters_3": [1, 2],
        "dashboard_aggregation_select": "yearly",
        "dashboard_period_date_from": "2020-01-01",
        "dashboard_period_date_to": "2024-12-31",
        "dashboard_map_show_only_selected": True,
        "dashboard_map_classification_cache": {"signature": ("old",), "values": {"1": 12.5}},
        "dashboard_map_pending_station_ids": [2],
        "dashboard_ignore_next_map_selection": True,
        "dashboard_stations_map_selected_only_1_2": {"selection": [1, 2]},
        "dashboard_map_selected_color": "#f59e0b",
        session.PERSISTED_FORM_VALUES_KEY: {
            "analysis_station": 1,
            "analysis_date_from": "2020-01-01",
        },
        "analysis_station": 1,
        "analysis_date_from": "2020-01-01",
    }
    monkeypatch.setattr(session.st, "session_state", state)

    session.clear_dashboard_context()

    assert state["access_token"] == "sample-token"
    assert state["cached_stations"] == [{"id": 1}]
    assert state["dashboard_map_selected_color"] == "#f59e0b"
    assert state[session.PERSISTED_FORM_VALUES_KEY] == {}
    assert "analysis_station" not in state
    assert "analysis_date_from" not in state
    assert state["selected_station_id"] is None
    assert state["selected_parameter_id"] is None
    assert state["dashboard_station_ids"] is None
    assert state["dashboard_date_from"] is None
    assert state["dashboard_date_to"] is None
    assert state["dashboard_aggregation"] == "monthly"
    assert state["dashboard_parameter_ids"] == []
    assert state["dashboard_map_show_only_selected"] is False
    assert state["dashboard_map_classification_cache"] == {}
    assert "dashboard_station_multiselect" not in state
    assert "dashboard_parameter" not in state
    assert "dashboard_parameter_3" not in state
    assert "dashboard_parameters_3" not in state
    assert "dashboard_aggregation_select" not in state
    assert "dashboard_period_date_from" not in state
    assert "dashboard_period_date_to" not in state
    assert "dashboard_map_pending_station_ids" not in state
    assert "dashboard_ignore_next_map_selection" not in state
    assert "dashboard_stations_map_selected_only_1_2" not in state


def test_restore_saved_analysis_set_updates_dashboard_and_analysis_context(monkeypatch) -> None:
    """Проверяет восстановление параметров из пользовательского сохранённого набора."""

    state = {
        "dashboard_filter_revision": 2,
        session.PERSISTED_FORM_VALUES_KEY: {},
    }
    monkeypatch.setattr(session.st, "session_state", state)

    restored = session.restore_saved_analysis_set(
        {
            "id": 9,
            "station_id": 20674,
            "parameter_id": 1,
            "selected_parameters": [1, 2],
            "period_start": "1995-01-01",
            "period_end": "2024-12-01",
            "aggregation": "monthly",
            "mode": "dashboard",
            "modes": ["dashboard", "forecast", "correlation", "report"],
            "session_snapshot": {
                "forecast_model": "neural_mlp",
                "forecast_horizon": 24,
                "forecast_date_from": "2000-01-01",
                "correlation_method": "spearman",
                "correlation_parameters": [1, 2, 3],
                "report_include_graphs": False,
                "dashboard_map_selected_color": "#f59e0b",
                "dashboard_filter_revision": 99,
            },
        }
    )

    assert restored["station_ids"] == [20674]
    assert state["dashboard_station_ids"] == [20674]
    assert state["selected_station_id"] == 20674
    assert state["selected_parameter_id"] == 1
    assert state["dashboard_date_from"] == date(1995, 1, 1)
    assert state["dashboard_date_to"] == date(2024, 12, 1)
    assert state["dashboard_filter_revision"] == 3
    assert state["dashboard_parameter_3"] == 1
    assert state["dashboard_parameters_3"] == [1, 2]
    assert state["dashboard_parameter_ids"] == [1, 2]
    assert state["dashboard_saved_set_modes"] == ["dashboard", "forecast", "correlation", "report"]
    assert state["analysis_station"] == 20674
    assert state["analysis_parameter"] == 1
    assert state[session.PERSISTED_FORM_VALUES_KEY]["analysis_date_from"] == date(1995, 1, 1)
    assert state["forecast_model"] == "neural_mlp"
    assert state["forecast_horizon"] == 24
    assert state["forecast_date_from"] == date(2000, 1, 1)
    assert state["correlation_method"] == "spearman"
    assert state["correlation_parameters"] == [1, 2, 3]
    assert state["report_include_graphs"] is False
    assert state["dashboard_map_selected_color"] == "#f59e0b"
    assert state[session.PERSISTED_FORM_VALUES_KEY]["forecast_model"] == "neural_mlp"
    assert restored["modes"] == ["dashboard", "forecast", "correlation", "report"]
    assert "dashboard_filter_revision" not in restored["restored_snapshot_keys"]
