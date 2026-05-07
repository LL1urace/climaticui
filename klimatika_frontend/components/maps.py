"""Map components."""

from __future__ import annotations

from typing import Any

import pandas as pd
import pydeck as pdk
import streamlit as st

from klimatika_frontend.utils.formatters import unwrap_records


def render_stations_map(payload: Any, value_key: str | None = None) -> None:
    df = pd.DataFrame(unwrap_records(payload))
    if df.empty:
        st.info("Станции для карты отсутствуют.")
        return

    lat_col = "latitude" if "latitude" in df.columns else "lat"
    lon_col = "longitude" if "longitude" in df.columns else "lon"
    if lat_col not in df.columns or lon_col not in df.columns:
        st.warning("Backend не вернул координаты станций.")
        return

    df = df.dropna(subset=[lat_col, lon_col]).copy()
    if df.empty:
        st.warning("У выбранных станций нет координат.")
        return

    df["tooltip"] = df.apply(
        lambda row: f"{row.get('name', 'Станция')}<br>{value_key}: {row.get(value_key)}" if value_key else str(row.get("name", "Станция")),
        axis=1,
    )
    layer = pdk.Layer(
        "ScatterplotLayer",
        data=df,
        get_position=[lon_col, lat_col],
        get_radius=45000,
        get_fill_color=[28, 91, 117, 180],
        pickable=True,
    )
    view_state = pdk.ViewState(latitude=float(df[lat_col].mean()), longitude=float(df[lon_col].mean()), zoom=3)
    st.pydeck_chart(pdk.Deck(layers=[layer], initial_view_state=view_state, tooltip={"html": "{tooltip}"}))

