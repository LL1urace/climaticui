"""Plotly chart helpers."""

from __future__ import annotations

from typing import Any

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from klimatika_frontend.utils.formatters import series_dataframe, unwrap_records


DEFAULT_CHART_COLOR = "#0d64d8"
CHART_PALETTE = [
    "#0d64d8",
    "#17b6d6",
    "#f59e0b",
    "#16a34a",
    "#dc2626",
    "#7c3aed",
    "#0891b2",
    "#be123c",
    "#4f46e5",
    "#65a30d",
]
MONTH_TICKS = list(range(1, 13))
MONTH_LABELS = ["Янв", "Фев", "Мар", "Апр", "Май", "Июн", "Июл", "Авг", "Сен", "Окт", "Ноя", "Дек"]
LINE_DASHES = ["solid", "dash", "dot", "dashdot", "longdash", "longdashdot"]


def _color_for_key(color_map: dict[Any, str] | None, key: Any) -> str | None:
    """Возвращает цвет для ключа графика с учётом строкового варианта ID.

    Args:
        color_map: Сопоставление идентификаторов и цветов.
        key: Ключ станции или категории.

    Returns:
        Hex-цвет или None, если цвет не задан.
    """

    if not color_map or key is None:
        return None
    return color_map.get(key) or color_map.get(str(key))


def render_timeseries_chart(payload: Any, title: str = "Временной ряд", value_label: str = "Значение") -> None:
    """Отображает линейный график временного ряда.

    Args:
        payload: JSON-ответ или список точек временного ряда.
        title: Заголовок графика.
        value_label: Подпись оси значений.

    Returns:
        None.
    """

    df = series_dataframe(payload)
    if df.empty or "date" not in df.columns or "value" not in df.columns:
        st.info("Временной ряд отсутствует в ответе backend.")
        return

    fig = go.Figure()
    fig.add_trace(go.Scatter(x=df["date"], y=df["value"], name=value_label, mode="lines+markers"))
    fig.update_layout(title=title, xaxis_title="Дата", yaxis_title=value_label, hovermode="x unified", height=440)
    st.plotly_chart(fig, use_container_width=True)


def render_multi_timeseries_chart(
    series_payloads: list[dict[str, Any]],
    title: str = "Динамика по станциям",
    value_label: str = "Значение",
    color_map: dict[Any, str] | None = None,
) -> None:
    """Отображает несколько временных рядов на одном линейном графике.

    Args:
        series_payloads: Список словарей со station_id, label и series.
        title: Заголовок графика.
        value_label: Подпись оси значений.
        color_map: Цвета линий по station_id.

    Returns:
        None.
    """

    fig = go.Figure()
    has_data = False

    for item in series_payloads:
        station_key = item.get("station_id") or item.get("id") or item.get("label")
        label = str(item.get("label") or station_key or "Станция")
        df = series_dataframe(item.get("series") or item.get("timeseries") or item.get("values") or item)
        if df.empty or not {"date", "value"}.issubset(df.columns):
            continue

        color = _color_for_key(color_map, station_key)
        trace_kwargs: dict[str, Any] = {
            "x": df["date"],
            "y": df["value"],
            "name": label,
            "mode": "lines+markers",
        }
        if color:
            trace_kwargs["line"] = {"color": color}
            trace_kwargs["marker"] = {"color": color}
        fig.add_trace(go.Scatter(**trace_kwargs))
        has_data = True

    if not has_data:
        st.info("Временные ряды для выбранных станций отсутствуют.")
        return

    fig.update_layout(title=title, xaxis_title="Дата", yaxis_title=value_label, hovermode="x unified", height=460)
    st.plotly_chart(fig, use_container_width=True)


def render_overlay_chart(series_payload: Any, overlays: dict[str, Any], title: str = "Результаты анализа") -> None:
    """Отображает исходный ряд вместе с дополнительными рядами анализа.

    Args:
        series_payload: JSON-данные исходного временного ряда.
        overlays: Словарь дополнительных рядов для наложения.
        title: Заголовок графика.

    Returns:
        None.
    """

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


def render_bar_chart(
    payload: Any,
    x_key: str = "name",
    y_key: str = "value",
    title: str = "Сравнение",
    color_key: str | None = None,
    color_map: dict[Any, str] | None = None,
) -> None:
    """Отображает горизонтальную столбчатую диаграмму.

    Args:
        payload: JSON-ответ или список записей для графика.
        x_key: Поле подписи категории.
        y_key: Поле числового значения.
        title: Заголовок графика.
        color_key: Поле, по которому выбирается цвет столбца.
        color_map: Цвета столбцов по значениям color_key.

    Returns:
        None.
    """

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

    bar_kwargs: dict[str, Any] = {"x": df[y_key], "y": df[x_key], "orientation": "h"}
    if color_map:
        source_key = color_key if color_key in df.columns else x_key
        bar_kwargs["marker_color"] = [
            _color_for_key(color_map, value) or DEFAULT_CHART_COLOR
            for value in df[source_key]
        ]

    fig = go.Figure(go.Bar(**bar_kwargs))
    fig.update_layout(title=title, xaxis_title="Значение", yaxis_title="", height=420)
    st.plotly_chart(fig, use_container_width=True)


def render_grouped_bar_chart(
    payload: Any,
    x_key: str,
    y_key: str,
    group_key: str,
    title: str = "Сравнение",
    color_map: dict[Any, str] | None = None,
) -> None:
    """Отображает сгруппированную столбчатую диаграмму.

    Args:
        payload: JSON-ответ или список записей для графика.
        x_key: Поле категории по оси X.
        y_key: Поле числового значения.
        group_key: Поле группы/серии.
        title: Заголовок графика.
        color_map: Цвета серий по значениям group_key.

    Returns:
        None.
    """

    records = unwrap_records(payload)
    df = pd.DataFrame(records)
    if df.empty:
        st.info("Данные для графика отсутствуют.")
        return
    if not {x_key, y_key, group_key}.issubset(df.columns):
        st.info("Backend не вернул подходящие поля для группового графика.")
        return

    fig = go.Figure()
    groups = list(dict.fromkeys(df[group_key].tolist()))
    for index, group in enumerate(groups):
        group_df = df[df[group_key] == group]
        color = _color_for_key(color_map, group) or CHART_PALETTE[index % len(CHART_PALETTE)]
        fig.add_trace(
            go.Bar(
                x=group_df[x_key],
                y=group_df[y_key],
                name=str(group),
                marker_color=color,
            )
        )

    fig.update_layout(title=title, xaxis_title="", yaxis_title="Значение", barmode="group", height=460)
    st.plotly_chart(fig, use_container_width=True)


def render_climatogram(payload: Any) -> None:
    """Отображает климатограмму температуры и осадков.

    Args:
        payload: JSON-ответ backend с месячными данными климатограммы.

    Returns:
        None.
    """

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


def _multi_climatogram_records(items: list[dict[str, Any]]) -> pd.DataFrame:
    """Преобразует несколько климатограмм в плоскую таблицу для графика.

    Args:
        items: Список результатов с данными станции, периода и JSON климатограммы.

    Returns:
        DataFrame с месячными значениями по всем комбинациям.
    """

    records: list[dict[str, Any]] = []
    for item in items:
        months = unwrap_records(item.get("result"), ("months", "values", "data", "items"))
        for month in months:
            month_value = month.get("month")
            temperature = month.get("temperature_mean") if "temperature_mean" in month else month.get("temperature")
            precipitation = month.get("precipitation_sum") if "precipitation_sum" in month else month.get("precipitation")
            records.append(
                {
                    "station_id": item.get("station_id"),
                    "station_name": item.get("station_name") or item.get("station_label") or "Станция",
                    "period_index": item.get("period_index"),
                    "period_label": item.get("period_label") or "Период",
                    "month": month_value,
                    "temperature_mean": temperature,
                    "precipitation_sum": precipitation,
                }
            )
    return pd.DataFrame(records)


def _multi_climatogram_group(row: pd.Series, overlay_stations: bool, overlay_periods: bool) -> str:
    """Возвращает название группы графика для выбранных режимов наложения.

    Args:
        row: Строка плоской таблицы климатограмм.
        overlay_stations: Накладывать ли станции внутри одного графика.
        overlay_periods: Накладывать ли периоды внутри одного графика.

    Returns:
        Название группы графика.
    """

    if overlay_stations and overlay_periods:
        return "Все станции и периоды"
    if overlay_stations:
        return str(row["period_label"])
    if overlay_periods:
        return str(row["station_name"])
    return f"{row['station_name']} · {row['period_label']}"


def _multi_climatogram_trace(row: pd.Series, overlay_stations: bool, overlay_periods: bool) -> str:
    """Возвращает подпись ряда для выбранных режимов наложения.

    Args:
        row: Строка плоской таблицы климатограмм.
        overlay_stations: Накладывать ли станции внутри одного графика.
        overlay_periods: Накладывать ли периоды внутри одного графика.

    Returns:
        Подпись линии/столбцов в легенде.
    """

    if overlay_stations and overlay_periods:
        return f"{row['station_name']} · {row['period_label']}"
    if overlay_stations:
        return str(row["station_name"])
    if overlay_periods:
        return str(row["period_label"])
    return "Климатограмма"


def render_multi_climatograms(
    items: list[dict[str, Any]],
    overlay_stations: bool = False,
    overlay_periods: bool = False,
    title: str = "Климатограмма",
    color_map: dict[Any, str] | None = None,
) -> None:
    """Отображает климатограммы для нескольких станций и периодов.

    Args:
        items: Список результатов с данными станции, периода и JSON климатограммы.
        overlay_stations: Накладывать метеостанции на один график внутри периода.
        overlay_periods: Накладывать периоды на один график внутри станции.
        title: Заголовок графика.
        color_map: Цвета по ключам `<station_id>:temperature` и `<station_id>:precipitation`.

    Returns:
        None.
    """

    df = _multi_climatogram_records(items)
    if df.empty:
        st.info("Данные климатограмм отсутствуют.")
        return

    required_columns = {"month", "temperature_mean", "precipitation_sum"}
    if not required_columns.issubset(df.columns):
        st.info("Backend не вернул поля температуры и осадков для климатограмм.")
        return

    df = df.copy()
    df["group_label"] = df.apply(
        lambda row: _multi_climatogram_group(row, overlay_stations, overlay_periods),
        axis=1,
    )
    df["trace_label"] = df.apply(
        lambda row: _multi_climatogram_trace(row, overlay_stations, overlay_periods),
        axis=1,
    )

    group_labels = list(dict.fromkeys(df["group_label"].tolist()))
    for group_label in group_labels:
        group = df[df["group_label"] == group_label]
        fig = go.Figure()
        trace_labels = list(dict.fromkeys(group["trace_label"].tolist()))
        for trace_index, trace_label in enumerate(trace_labels):
            trace = group[group["trace_label"] == trace_label].sort_values("month")
            first_row = trace.iloc[0]
            station_key = first_row.get("station_id")
            temperature_color = (
                _color_for_key(color_map, f"{station_key}:temperature")
                or CHART_PALETTE[trace_index % len(CHART_PALETTE)]
            )
            precipitation_color = (
                _color_for_key(color_map, f"{station_key}:precipitation")
                or temperature_color
            )
            legend_group = f"{group_label}-{trace_label}"
            fig.add_trace(
                go.Bar(
                    x=trace["month"],
                    y=trace["precipitation_sum"],
                    name=f"Осадки · {trace_label}",
                    yaxis="y2",
                    opacity=0.34,
                    marker_color=precipitation_color,
                    legendgroup=legend_group,
                )
            )
            fig.add_trace(
                go.Scatter(
                    x=trace["month"],
                    y=trace["temperature_mean"],
                    name=f"Температура · {trace_label}",
                    mode="lines+markers",
                    line={"color": temperature_color, "dash": LINE_DASHES[trace_index % len(LINE_DASHES)]},
                    marker={"color": temperature_color},
                    legendgroup=legend_group,
                )
            )

        chart_title = title if len(group_labels) == 1 else f"{title}: {group_label}"
        fig.update_layout(
            title=chart_title,
            xaxis_title="Месяц",
            xaxis={"tickmode": "array", "tickvals": MONTH_TICKS, "ticktext": MONTH_LABELS},
            yaxis_title="Температура",
            yaxis2={"title": "Осадки", "overlaying": "y", "side": "right"},
            hovermode="x unified",
            barmode="group",
            height=500,
        )
        st.plotly_chart(fig, use_container_width=True)
