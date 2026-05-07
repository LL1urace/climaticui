"""Plotly chart helpers."""

from __future__ import annotations

from typing import Any

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from klimatika_frontend.utils.formatters import series_dataframe, unwrap_records


def render_timeseries_chart(payload: Any, title: str = "Временной ряд", value_label: str = "Значение") -> None:
    df = series_dataframe(payload)
    if df.empty or "date" not in df.columns or "value" not in df.columns:
        st.info("Временной ряд отсутствует в ответе backend.")
        return

    fig = go.Figure()
    fig.add_trace(go.Scatter(x=df["date"], y=df["value"], name=value_label, mode="lines+markers"))
    fig.update_layout(title=title, xaxis_title="Дата", yaxis_title=value_label, hovermode="x unified", height=440)
    st.plotly_chart(fig, use_container_width=True)


def render_overlay_chart(series_payload: Any, overlays: dict[str, Any], title: str = "Результаты анализа") -> None:
    base_df = series_dataframe(series_payload)
    fig = go.Figure()
    has_data = False

    if not base_df.empty and {"date", "value"}.issubset(base_df.columns):
        fig.add_trace(go.Scatter(x=base_df["date"], y=base_df["value"], name="Исходный ряд", mode="lines"))
        has_data = True

    for name, payload in overlays.items():
        df = series_dataframe(payload)
        if df.empty or not {"date", "value"}.issubset(df.columns):
            continue
        fig.add_trace(go.Scatter(x=df["date"], y=df["value"], name=name, mode="lines"))
        has_data = True

    if not has_data:
        st.info("Данные для графика отсутствуют.")
        return

    fig.update_layout(title=title, xaxis_title="Дата", yaxis_title="Значение", hovermode="x unified", height=480)
    st.plotly_chart(fig, use_container_width=True)


def render_bar_chart(payload: Any, x_key: str = "name", y_key: str = "value", title: str = "Сравнение") -> None:
    records = unwrap_records(payload)
    df = pd.DataFrame(records)
    if df.empty:
        st.info("Данные для столбчатого графика отсутствуют.")
        return

    if x_key not in df.columns:
        for candidate in ("name", "station_name", "period", "label", "code"):
            if candidate in df.columns:
                x_key = candidate
                break

    if y_key not in df.columns:
        for candidate in ("value", "mean", "max", "min", "sum", "std"):
            if candidate in df.columns:
                y_key = candidate
                break

    if x_key not in df.columns or y_key not in df.columns:
        st.info("Backend не вернул подходящие поля для столбчатого графика.")
        return
    fig = go.Figure(go.Bar(x=df[y_key], y=df[x_key], orientation="h"))
    fig.update_layout(title=title, xaxis_title="Значение", yaxis_title="", height=420)
    st.plotly_chart(fig, use_container_width=True)


def render_climatogram(payload: Any) -> None:
    records = unwrap_records(payload, ("months", "values", "data", "items"))
    df = pd.DataFrame(records)
    if df.empty:
        st.info("Данные климатограммы отсутствуют.")
        return

    month_col = "month" if "month" in df.columns else df.columns[0]
    temp_col = "temperature_mean" if "temperature_mean" in df.columns else "temperature"
    precip_col = "precipitation_sum" if "precipitation_sum" in df.columns else "precipitation"
    if temp_col not in df.columns or precip_col not in df.columns:
        st.info("Backend не вернул поля температуры и осадков для климатограммы.")
        return

    fig = go.Figure()
    fig.add_trace(go.Bar(x=df[month_col], y=df[precip_col], name="Осадки", yaxis="y2", opacity=0.55))
    fig.add_trace(go.Scatter(x=df[month_col], y=df[temp_col], name="Температура", mode="lines+markers"))
    fig.update_layout(
        title="Климатограмма",
        xaxis_title="Месяц",
        yaxis_title="Температура",
        yaxis2={"title": "Осадки", "overlaying": "y", "side": "right"},
        hovermode="x unified",
        height=480,
    )
    st.plotly_chart(fig, use_container_width=True)
