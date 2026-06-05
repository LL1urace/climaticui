from __future__ import annotations

from app.data_sources.local_observations import local_raw_observation_rows


def test_local_raw_observation_rows_returns_full_downloaded_period() -> None:
    """Проверяет сырой срез из локального daily pack без месячной агрегации."""

    rows = local_raw_observation_rows(20674, 1, "2020-01-01", "2020-12-31")

    assert len(rows) == 366
    assert rows[0]["date"] == "2020-01-01"
    assert rows[-1]["date"] == "2020-12-31"
    assert rows[0]["source_name"] == "local_meteostat_daily_csv_gz"
    assert rows[0]["source_url"].endswith("/daily/2020/20674.csv.gz")


def test_local_raw_observation_rows_supports_daily_humidity() -> None:
    """Проверяет чтение влажности из daily CSV.gz."""

    rows = local_raw_observation_rows(20674, 3, "2020-01-01", "2020-12-31")

    assert len(rows) == 366
    assert rows[0]["value_column"] == "rhum"
    assert rows[0]["source_name"] == "local_meteostat_daily_csv_gz"
