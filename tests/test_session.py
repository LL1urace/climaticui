from __future__ import annotations

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
        "dashboard_aggregation_select": "yearly",
        "dashboard_period_date_from": "2020-01-01",
        "dashboard_period_date_to": "2024-12-31",
        "dashboard_map_show_only_selected": True,
        "dashboard_map_classification_cache": {"signature": ("old",), "values": {"1": 12.5}},
        "dashboard_map_pending_station_ids": [2],
        "dashboard_ignore_next_map_selection": True,
        "dashboard_stations_map_selected_only_1_2": {"selection": [1, 2]},
        "dashboard_map_selected_color": "#f59e0b",
    }
    monkeypatch.setattr(session.st, "session_state", state)

    session.clear_dashboard_context()

    assert state["access_token"] == "sample-token"
    assert state["cached_stations"] == [{"id": 1}]
    assert state["dashboard_map_selected_color"] == "#f59e0b"
    assert state["selected_station_id"] is None
    assert state["selected_parameter_id"] is None
    assert state["dashboard_station_ids"] is None
    assert state["dashboard_date_from"] is None
    assert state["dashboard_date_to"] is None
    assert state["dashboard_aggregation"] == "monthly"
    assert state["dashboard_map_show_only_selected"] is False
    assert state["dashboard_map_classification_cache"] == {}
    assert "dashboard_station_multiselect" not in state
    assert "dashboard_aggregation_select" not in state
    assert "dashboard_period_date_from" not in state
    assert "dashboard_period_date_to" not in state
    assert "dashboard_map_pending_station_ids" not in state
    assert "dashboard_ignore_next_map_selection" not in state
    assert "dashboard_stations_map_selected_only_1_2" not in state
