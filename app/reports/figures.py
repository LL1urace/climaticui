"""Plotly figure builders for PDF reports."""

from __future__ import annotations

from typing import Any

import pandas as pd
import plotly.graph_objects as go

from app.components.charts import (
    CHART_PALETTE,
    DEFAULT_CHART_COLOR,
    LINE_DASHES,
    MONTH_LABELS,
    MONTH_TICKS,
    _axis_label,
    _closed_month_trace,
    _color_for_key,
    _hex_to_rgba,
    _multi_climatogram_group,
    _multi_climatogram_trace,
    _records_from_keys,
    climatogram_records_dataframe,
    climatogram_scatter_dataframe,
)
from app.utils.formatters import series_dataframe, unwrap_records


def _apply_report_layout(fig: go.Figure, height: int = 520) -> go.Figure:
    """Применяет единый визуальный стиль графиков для PDF.

    Args:
        fig: Plotly-фигура.
        height: Высота графика в пикселях.

    Returns:
        Фигура с обновлённым оформлением.
    """

    fig.update_layout(
        template="plotly_white",
        font={"family": "DejaVu Sans, Arial, sans-serif", "size": 13, "color": "#07111f"},
        paper_bgcolor="#ffffff",
        plot_bgcolor="#ffffff",
        margin={"l": 58, "r": 40, "t": 78, "b": 58},
        height=height,
        legend={"orientation": "h", "yanchor": "bottom", "y": 1.02, "xanchor": "left", "x": 0},
    )
    fig.update_xaxes(showgrid=True, gridcolor="rgba(148, 163, 184, 0.25)", zeroline=False)
    fig.update_yaxes(showgrid=True, gridcolor="rgba(148, 163, 184, 0.25)", zeroline=False)
    return fig


def _empty_figure(title: str, message: str = "Данные отсутствуют") -> go.Figure:
    """Создаёт пустую фигуру с пояснением.

    Args:
        title: Заголовок графика.
        message: Текст пояснения в центре графика.

    Returns:
        Plotly-фигура без рядов данных.
    """

    fig = go.Figure()
    fig.add_annotation(
        text=message,
        xref="paper",
        yref="paper",
        x=0.5,
        y=0.5,
        showarrow=False,
        font={"size": 18, "color": "#475569"},
    )
    fig.update_layout(title=title, xaxis={"visible": False}, yaxis={"visible": False})
    return _apply_report_layout(fig, height=360)


def _numeric_column(df: pd.DataFrame, preferred: str | None = None) -> str | None:
    """Выбирает числовую колонку таблицы.

    Args:
        df: Таблица с данными.
        preferred: Предпочитаемое имя колонки.

    Returns:
        Имя числовой колонки или None.
    """

    if preferred and preferred in df.columns and pd.to_numeric(df[preferred], errors="coerce").notna().any():
        return preferred
    for candidate in ("value", "mean", "max", "min", "sum", "std", "median", "count"):
        if candidate in df.columns and pd.to_numeric(df[candidate], errors="coerce").notna().any():
            return candidate
    for column in df.columns:
        if pd.to_numeric(df[column], errors="coerce").notna().any():
            return str(column)
    return None


def _category_column(df: pd.DataFrame, preferred: str | None = None) -> str | None:
    """Выбирает категориальную колонку таблицы.

    Args:
        df: Таблица с данными.
        preferred: Предпочитаемое имя колонки.

    Returns:
        Имя категориальной колонки или None.
    """

    if preferred and preferred in df.columns:
        return preferred
    for candidate in ("name", "station_name", "period", "label", "code", "month"):
        if candidate in df.columns:
            return candidate
    return str(df.columns[0]) if len(df.columns) else None


def build_timeseries_figure(payload: Any, title: str = "Временной ряд", value_label: str = "Значение") -> go.Figure:
    """Строит фигуру временного ряда.

    Args:
        payload: JSON-ответ или список точек временного ряда.
        title: Заголовок графика.
        value_label: Подпись оси значений.

    Returns:
        Plotly-фигура временного ряда.
    """

    df = series_dataframe(payload)
    if df.empty or not {"date", "value"}.issubset(df.columns):
        return _empty_figure(title, "Временной ряд отсутствует")

    fig = go.Figure()
    fig.add_trace(
        go.Scatter(
            x=df["date"],
            y=pd.to_numeric(df["value"], errors="coerce"),
            name=value_label,
            mode="lines+markers",
            line={"color": DEFAULT_CHART_COLOR, "width": 2.6},
            marker={"size": 6, "color": DEFAULT_CHART_COLOR},
        )
    )
    fig.update_layout(title=title, xaxis_title="Дата", yaxis_title=value_label, hovermode="x unified")
    return _apply_report_layout(fig)


def build_multi_timeseries_figure(
    series_payloads: list[dict[str, Any]],
    title: str = "Динамика по станциям",
    value_label: str = "Значение",
    color_map: dict[Any, str] | None = None,
) -> go.Figure:
    """Строит фигуру с несколькими временными рядами.

    Args:
        series_payloads: Список словарей со station_id, label и series.
        title: Заголовок графика.
        value_label: Подпись оси значений.
        color_map: Цвета линий по station_id.

    Returns:
        Plotly-фигура с несколькими рядами.
    """

    fig = go.Figure()
    has_data = False
    for index, item in enumerate(series_payloads or []):
        station_key = item.get("station_id") or item.get("id") or item.get("label")
        label = str(item.get("label") or station_key or "Станция")
        df = series_dataframe(item.get("series") or item.get("timeseries") or item.get("values") or item)
        if df.empty or not {"date", "value"}.issubset(df.columns):
            continue
        color = _color_for_key(color_map, station_key) or CHART_PALETTE[index % len(CHART_PALETTE)]
        fig.add_trace(
            go.Scatter(
                x=df["date"],
                y=pd.to_numeric(df["value"], errors="coerce"),
                name=label,
                mode="lines+markers",
                line={"color": color, "width": 2.4},
                marker={"size": 5, "color": color},
            )
        )
        has_data = True

    if not has_data:
        return _empty_figure(title, "Временные ряды отсутствуют")
    fig.update_layout(title=title, xaxis_title="Дата", yaxis_title=value_label, hovermode="x unified")
    return _apply_report_layout(fig)


def build_overlay_figure(series_payload: Any, overlays: dict[str, Any], title: str = "Результаты анализа") -> go.Figure:
    """Строит фигуру исходного ряда с наложенными расчётными рядами.

    Args:
        series_payload: JSON-данные исходного временного ряда.
        overlays: Словарь дополнительных рядов для наложения.
        title: Заголовок графика.

    Returns:
        Plotly-фигура с исходным рядом и оверлеями.
    """

    fig = go.Figure()
    base_df = series_dataframe(series_payload)
    has_data = False
    if not base_df.empty and {"date", "value"}.issubset(base_df.columns):
        fig.add_trace(
            go.Scatter(
                x=base_df["date"],
                y=pd.to_numeric(base_df["value"], errors="coerce"),
                name="Исходный ряд",
                mode="lines",
                line={"color": "#07111f", "width": 2.2},
            )
        )
        has_data = True

    for index, (name, payload) in enumerate((overlays or {}).items()):
        df = series_dataframe(payload)
        if df.empty or not {"date", "value"}.issubset(df.columns):
            continue
        fig.add_trace(
            go.Scatter(
                x=df["date"],
                y=pd.to_numeric(df["value"], errors="coerce"),
                name=name,
                mode="lines",
                line={"color": CHART_PALETTE[index % len(CHART_PALETTE)], "width": 2.6},
            )
        )
        has_data = True

    if not has_data:
        return _empty_figure(title, "Данные для графика отсутствуют")
    fig.update_layout(title=title, xaxis_title="Дата", yaxis_title="Значение", hovermode="x unified")
    return _apply_report_layout(fig)


def build_anomaly_figure(anomalies_payload: Any, title: str = "График аномалий") -> go.Figure:
    """Строит столбчатый график климатических аномалий.

    Args:
        anomalies_payload: JSON результата метода `anomalies`.
        title: Заголовок графика.

    Returns:
        Plotly-фигура аномалий.
    """

    df = series_dataframe(anomalies_payload)
    if df.empty or not {"date", "value"}.issubset(df.columns):
        return _empty_figure(title, "Аномалии отсутствуют")

    values = pd.to_numeric(df["value"], errors="coerce")
    colors = ["#0d64d8" if value >= 0 else "#07111f" for value in values.fillna(0)]
    fig = go.Figure(go.Bar(x=df["date"], y=values, name="Аномалия", marker_color=colors, opacity=0.86))
    fig.add_hline(y=0, line_dash="dash", line_color="#64748b")
    fig.update_layout(title=title, xaxis_title="Дата", yaxis_title="Отклонение", hovermode="x unified")
    return _apply_report_layout(fig)


def build_decomposition_figure(payload: Any, title: str = "Сезонная декомпозиция") -> go.Figure:
    """Строит график компонентов сезонной декомпозиции.

    Args:
        payload: JSON результата метода `seasonal_decomposition`.
        title: Заголовок графика.

    Returns:
        Plotly-фигура компонентов декомпозиции.
    """

    if not isinstance(payload, dict) or payload.get("status") == "failed":
        return _empty_figure(title, "Декомпозиция отсутствует")

    components = payload.get("components") if isinstance(payload.get("components"), dict) else payload
    component_labels = {
        "trend": "Трендовая компонента",
        "seasonal": "Сезонная компонента",
        "residual": "Остаточная компонента",
    }
    fig = go.Figure()
    has_data = False
    for index, (component_key, component_label) in enumerate(component_labels.items()):
        df = series_dataframe(components.get(component_key) if isinstance(components, dict) else None)
        if df.empty or not {"date", "value"}.issubset(df.columns):
            continue
        fig.add_trace(
            go.Scatter(
                x=df["date"],
                y=pd.to_numeric(df["value"], errors="coerce"),
                name=component_label,
                mode="lines",
                line={"color": CHART_PALETTE[index % len(CHART_PALETTE)], "width": 2.4},
            )
        )
        has_data = True

    if not has_data:
        return _empty_figure(title, "Backend не вернул компоненты")
    fig.update_layout(title=title, xaxis_title="Дата", yaxis_title="Значение", hovermode="x unified")
    return _apply_report_layout(fig)


def build_extremes_figure(series_payload: Any, extremes_payload: Any, title: str = "Экстремальные значения") -> go.Figure:
    """Строит временной ряд с отмеченными экстремумами.

    Args:
        series_payload: Исходный временной ряд.
        extremes_payload: JSON результата метода `extremes`.
        title: Заголовок графика.

    Returns:
        Plotly-фигура экстремумов.
    """

    base_df = series_dataframe(series_payload)
    values_df = pd.DataFrame(_records_from_keys(extremes_payload, ("values", "points", "data", "items")))
    if base_df.empty or not {"date", "value"}.issubset(base_df.columns):
        base_df = values_df
    if base_df.empty or not {"date", "value"}.issubset(base_df.columns):
        return _empty_figure(title, "Данные экстремумов отсутствуют")

    fig = go.Figure()
    fig.add_trace(
        go.Scatter(
            x=base_df["date"],
            y=pd.to_numeric(base_df["value"], errors="coerce"),
            name="Временной ряд",
            mode="lines",
            line={"color": DEFAULT_CHART_COLOR, "width": 2.2},
        )
    )

    if not values_df.empty and {"date", "value", "kind"}.issubset(values_df.columns):
        high_df = values_df[values_df["kind"] == "high"]
        low_df = values_df[values_df["kind"] == "low"]
    else:
        high_df = pd.DataFrame(_records_from_keys(extremes_payload, ("maxima", "maximums", "high_extremes")))
        low_df = pd.DataFrame(_records_from_keys(extremes_payload, ("minima", "minimums", "low_extremes")))

    if not high_df.empty and {"date", "value"}.issubset(high_df.columns):
        fig.add_trace(
            go.Scatter(
                x=high_df["date"],
                y=pd.to_numeric(high_df["value"], errors="coerce"),
                name="Высокие экстремумы",
                mode="markers",
                marker={"size": 11, "color": "#17b6d6"},
            )
        )
    if not low_df.empty and {"date", "value"}.issubset(low_df.columns):
        fig.add_trace(
            go.Scatter(
                x=low_df["date"],
                y=pd.to_numeric(low_df["value"], errors="coerce"),
                name="Низкие экстремумы",
                mode="markers",
                marker={"size": 11, "color": "#07111f"},
            )
        )

    thresholds = extremes_payload.get("thresholds") if isinstance(extremes_payload, dict) else {}
    if isinstance(thresholds, dict):
        if thresholds.get("p95") is not None:
            fig.add_hline(y=thresholds["p95"], line_dash="dash", line_color="#17b6d6", annotation_text="p95")
        if thresholds.get("p05") is not None:
            fig.add_hline(y=thresholds["p05"], line_dash="dash", line_color="#07111f", annotation_text="p05")

    fig.update_layout(title=title, xaxis_title="Дата", yaxis_title="Значение", hovermode="x unified")
    return _apply_report_layout(fig)


def build_bar_chart_figure(
    payload: Any,
    x_key: str = "name",
    y_key: str = "value",
    title: str = "Сравнение",
    color_key: str | None = None,
    color_map: dict[Any, str] | None = None,
) -> go.Figure:
    """Строит горизонтальную столбчатую диаграмму.

    Args:
        payload: JSON-ответ или список записей для графика.
        x_key: Поле подписи категории.
        y_key: Поле числового значения.
        title: Заголовок графика.
        color_key: Поле, по которому выбирается цвет столбца.
        color_map: Цвета столбцов по значениям color_key.

    Returns:
        Plotly-фигура столбчатой диаграммы.
    """

    df = pd.DataFrame(unwrap_records(payload))
    if df.empty:
        return _empty_figure(title, "Данные для диаграммы отсутствуют")

    x_key = _category_column(df, x_key) or x_key
    y_key = _numeric_column(df, y_key) or y_key
    if x_key not in df.columns or y_key not in df.columns:
        return _empty_figure(title, "Подходящие поля не найдены")

    marker_color = DEFAULT_CHART_COLOR
    if color_map:
        source_key = color_key if color_key and color_key in df.columns else x_key
        marker_color = [_color_for_key(color_map, value) or DEFAULT_CHART_COLOR for value in df[source_key]]
    fig = go.Figure(
        go.Bar(
            x=pd.to_numeric(df[y_key], errors="coerce"),
            y=df[x_key],
            orientation="h",
            marker_color=marker_color,
        )
    )
    fig.update_layout(title=title, xaxis_title="Значение", yaxis_title="")
    return _apply_report_layout(fig, height=440)


def build_grouped_bar_chart_figure(
    payload: Any,
    x_key: str,
    y_key: str,
    group_key: str,
    title: str = "Сравнение",
    color_map: dict[Any, str] | None = None,
) -> go.Figure:
    """Строит сгруппированную столбчатую диаграмму.

    Args:
        payload: JSON-ответ или список записей для графика.
        x_key: Поле категории по оси X.
        y_key: Поле числового значения.
        group_key: Поле группы или серии.
        title: Заголовок графика.
        color_map: Цвета серий по значениям group_key.

    Returns:
        Plotly-фигура сгруппированной диаграммы.
    """

    df = pd.DataFrame(unwrap_records(payload))
    if df.empty:
        return _empty_figure(title, "Данные для графика отсутствуют")
    if y_key not in df.columns:
        y_key = _numeric_column(df, y_key) or y_key
    if not {x_key, y_key, group_key}.issubset(df.columns):
        return _empty_figure(title, "Подходящие поля не найдены")

    fig = go.Figure()
    groups = list(dict.fromkeys(df[group_key].tolist()))
    for index, group in enumerate(groups):
        group_df = df[df[group_key] == group]
        color = _color_for_key(color_map, group) or CHART_PALETTE[index % len(CHART_PALETTE)]
        fig.add_trace(
            go.Bar(
                x=group_df[x_key],
                y=pd.to_numeric(group_df[y_key], errors="coerce"),
                name=str(group),
                marker_color=color,
            )
        )
    fig.update_layout(title=title, xaxis_title="", yaxis_title="Значение", barmode="group")
    return _apply_report_layout(fig)


def build_correlation_heatmap_figure(payload: Any, title: str = "Корреляционная матрица") -> go.Figure:
    """Строит heatmap корреляционной матрицы.

    Args:
        payload: JSON результата корреляционного анализа.
        title: Заголовок графика.

    Returns:
        Plotly-фигура корреляционной матрицы.
    """

    if not isinstance(payload, dict):
        return _empty_figure(title, "Корреляционная матрица отсутствует")

    labels = payload.get("labels") or [item.get("name") for item in payload.get("parameters", []) if isinstance(item, dict)]
    matrix = payload.get("matrix")
    if isinstance(matrix, list) and matrix and isinstance(matrix[0], dict):
        row_labels = [row.get("parameter") or row.get("name") or row.get("label") for row in matrix]
        labels = labels or [label for label in row_labels if label]
        value_keys = [label for label in labels if label in matrix[0]]
        if value_keys:
            matrix = [[row.get(label) for label in value_keys] for row in matrix]
            labels = value_keys
    if not labels or not matrix:
        return _empty_figure(title, "Backend не вернул матрицу")

    fig = go.Figure(
        go.Heatmap(
            z=matrix,
            x=labels,
            y=labels,
            zmin=-1,
            zmax=1,
            colorscale=[[0, "#07111f"], [0.5, "#f8fbff"], [1, "#17b6d6"]],
            text=matrix,
            texttemplate="%{text:.2f}",
            hovertemplate="%{y} x %{x}: %{z:.3f}<extra></extra>",
        )
    )
    fig.update_layout(title=title)
    return _apply_report_layout(fig)


def build_correlation_scatter_figures(payload: Any, title: str = "Диаграммы корреляций") -> list[go.Figure]:
    """Строит scatter-графики пар параметров.

    Args:
        payload: JSON результата корреляционного анализа.
        title: Заголовок группы графиков.

    Returns:
        Список Plotly-фигур для пар параметров.
    """

    figures: list[go.Figure] = []
    pairs = _records_from_keys(payload, ("pairs", "results", "data", "items"))
    for pair in pairs:
        points = pd.DataFrame(_records_from_keys(pair, ("points", "values", "data", "items")))
        if points.empty or not {"x", "y"}.issubset(points.columns):
            continue
        x_name = pair.get("x_parameter_name") or pair.get("x") or "X"
        y_name = pair.get("y_parameter_name") or pair.get("y") or "Y"
        correlation = pair.get("correlation")
        fig = go.Figure()
        fig.add_trace(
            go.Scatter(
                x=pd.to_numeric(points["x"], errors="coerce"),
                y=pd.to_numeric(points["y"], errors="coerce"),
                name="Наблюдения",
                mode="markers",
                marker={"size": 9, "color": DEFAULT_CHART_COLOR, "opacity": 0.72},
                text=points["date"] if "date" in points.columns else None,
            )
        )
        chart_title = f"{x_name} x {y_name}" + (f" · r={correlation}" if correlation is not None else "")
        fig.update_layout(title=chart_title, xaxis_title=str(x_name), yaxis_title=str(y_name))
        figures.append(_apply_report_layout(fig, height=440))
    if not figures:
        figures.append(_empty_figure(title, "Пары параметров отсутствуют"))
    return figures


def build_station_map_figure(stations: list[dict[str, Any]], title: str = "Карта метеостанций") -> go.Figure:
    """Строит статичную карту станций на координатной плоскости.

    Args:
        stations: Список записей станций с latitude и longitude.
        title: Заголовок графика.

    Returns:
        Plotly-фигура, пригодная для экспорта в PDF.
    """

    df = pd.DataFrame(stations or [])
    if df.empty or not {"latitude", "longitude"}.issubset(df.columns):
        return _empty_figure(title, "Координаты станций отсутствуют")

    df = df.copy()
    df["latitude"] = pd.to_numeric(df["latitude"], errors="coerce")
    df["longitude"] = pd.to_numeric(df["longitude"], errors="coerce")
    df = df.dropna(subset=["latitude", "longitude"])
    if df.empty:
        return _empty_figure(title, "Координаты станций отсутствуют")
    label_col = "name" if "name" in df.columns else "station_name" if "station_name" in df.columns else None
    labels = df[label_col] if label_col else None
    fig = go.Figure()
    fig.add_trace(
        go.Scatter(
            x=df["longitude"],
            y=df["latitude"],
            mode="markers+text",
            text=labels,
            textposition="top center",
            marker={"size": 13, "color": DEFAULT_CHART_COLOR, "line": {"color": "#07111f", "width": 1}},
            name="Метеостанции",
        )
    )
    fig.update_layout(title=title, xaxis_title="Долгота", yaxis_title="Широта")
    return _apply_report_layout(fig, height=500)


def _climatogram_grouped_dataframe(
    items: list[dict[str, Any]],
    overlay_stations: bool,
    overlay_periods: bool,
) -> pd.DataFrame:
    """Готовит таблицу климатограмм с группами и рядами.

    Args:
        items: Результаты климатограмм.
        overlay_stations: Накладывать ли станции внутри одного графика.
        overlay_periods: Накладывать ли периоды внутри одного графика.

    Returns:
        DataFrame с колонками group_label и trace_label.
    """

    df = climatogram_records_dataframe(items)
    if df.empty:
        return df
    df = df.copy()
    df["group_label"] = df.apply(
        lambda row: _multi_climatogram_group(row, overlay_stations, overlay_periods),
        axis=1,
    )
    df["trace_label"] = df.apply(
        lambda row: _multi_climatogram_trace(row, overlay_stations, overlay_periods),
        axis=1,
    )
    return df


def build_climatogram_figures(
    items: list[dict[str, Any]],
    overlay_stations: bool = False,
    overlay_periods: bool = False,
    title: str = "Климатограмма",
    color_map: dict[Any, str] | None = None,
) -> list[go.Figure]:
    """Строит обычные климатограммы температуры и осадков.

    Args:
        items: Список результатов с данными станции, периода и JSON климатограммы.
        overlay_stations: Накладывать метеостанции на один график внутри периода.
        overlay_periods: Накладывать периоды на один график внутри станции.
        title: Заголовок графика.
        color_map: Цвета по ключам `<station_id>:temperature` и `<station_id>:precipitation`.

    Returns:
        Список Plotly-фигур климатограмм.
    """

    df = _climatogram_grouped_dataframe(items, overlay_stations, overlay_periods)
    required_columns = {"month", "temperature_mean", "precipitation_sum"}
    if df.empty or not required_columns.issubset(df.columns):
        return [_empty_figure(title, "Данные климатограмм отсутствуют")]

    figures: list[go.Figure] = []
    for group_label in list(dict.fromkeys(df["group_label"].tolist())):
        group = df[df["group_label"] == group_label]
        fig = go.Figure()
        for trace_index, trace_label in enumerate(list(dict.fromkeys(group["trace_label"].tolist()))):
            trace = group[group["trace_label"] == trace_label].sort_values("month_order")
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
                    y=pd.to_numeric(trace["precipitation_sum"], errors="coerce"),
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
                    y=pd.to_numeric(trace["temperature_mean"], errors="coerce"),
                    name=f"Температура · {trace_label}",
                    mode="lines+markers",
                    line={"color": temperature_color, "dash": LINE_DASHES[trace_index % len(LINE_DASHES)]},
                    marker={"color": temperature_color},
                    legendgroup=legend_group,
                )
            )
        chart_title = title if df["group_label"].nunique() == 1 else f"{title}: {group_label}"
        fig.update_layout(
            title=chart_title,
            xaxis_title="Месяц",
            xaxis={"tickmode": "array", "tickvals": MONTH_TICKS, "ticktext": MONTH_LABELS},
            yaxis_title="Температура",
            yaxis2={"title": "Осадки", "overlaying": "y", "side": "right"},
            hovermode="x unified",
            barmode="group",
        )
        figures.append(_apply_report_layout(fig, height=540))
    return figures


def build_climatogram_scatter_figures(
    items: list[dict[str, Any]],
    overlay_stations: bool = False,
    overlay_periods: bool = False,
    x_axis: str = "temperature_mean",
    y_axis: str = "precipitation_sum",
    connect_months: bool = True,
    close_polygon: bool = True,
    show_labels: bool = True,
    title: str = "Точечная климатограмма",
    color_map: dict[Any, str] | None = None,
) -> list[go.Figure]:
    """Строит точечные климатограммы для отчёта.

    Args:
        items: Список результатов климатограмм.
        overlay_stations: Накладывать метеостанции на один график внутри периода.
        overlay_periods: Накладывать периоды на один график внутри станции.
        x_axis: Ключ поля горизонтальной оси.
        y_axis: Ключ поля вертикальной оси.
        connect_months: Соединять ли месяцы линией.
        close_polygon: Замыкать ли годовой ход в многоугольник.
        show_labels: Подписывать ли точки месяцами.
        title: Заголовок графика.
        color_map: Цвета по станциям.

    Returns:
        Список Plotly-фигур точечной климатограммы.
    """

    df = climatogram_scatter_dataframe(items, x_axis, y_axis)
    if df.empty:
        return [_empty_figure(title, "Данные для точечной климатограммы отсутствуют")]
    df = df.copy()
    df["group_label"] = df.apply(
        lambda row: _multi_climatogram_group(row, overlay_stations, overlay_periods),
        axis=1,
    )
    df["trace_label"] = df.apply(
        lambda row: _multi_climatogram_trace(row, overlay_stations, overlay_periods),
        axis=1,
    )

    figures: list[go.Figure] = []
    for group_label in list(dict.fromkeys(df["group_label"].tolist())):
        group = df[df["group_label"] == group_label]
        fig = go.Figure()
        for trace_index, trace_label in enumerate(list(dict.fromkeys(group["trace_label"].tolist()))):
            trace = group[group["trace_label"] == trace_label].sort_values("month_order")
            if trace.empty:
                continue
            first_row = trace.iloc[0]
            station_key = first_row.get("station_id")
            color = (
                _color_for_key(color_map, f"{station_key}:temperature")
                or _color_for_key(color_map, f"{station_key}:precipitation")
                or CHART_PALETTE[trace_index % len(CHART_PALETTE)]
            )
            polygon_trace = _closed_month_trace(trace) if connect_months and close_polygon else trace
            if connect_months and close_polygon and len(polygon_trace) > len(trace):
                fig.add_trace(
                    go.Scatter(
                        x=polygon_trace[x_axis],
                        y=polygon_trace[y_axis],
                        name=f"Контур · {trace_label}",
                        mode="lines",
                        showlegend=False,
                        hoverinfo="skip",
                        fill="toself",
                        fillcolor=_hex_to_rgba(color, 0.12),
                        line={"color": color, "dash": LINE_DASHES[trace_index % len(LINE_DASHES)], "width": 2.8},
                    )
                )
            mode = "lines+markers" if connect_months else "markers"
            if connect_months and close_polygon:
                mode = "markers"
            if show_labels:
                mode = f"{mode}+text"
            fig.add_trace(
                go.Scatter(
                    x=trace[x_axis],
                    y=trace[y_axis],
                    name=str(trace_label),
                    mode=mode,
                    text=trace["month_sequence_label"].tolist() if show_labels else None,
                    textposition="top center",
                    marker={"size": 12, "color": color, "line": {"color": "#f8fbff", "width": 1.4}},
                    line={"color": color, "dash": LINE_DASHES[trace_index % len(LINE_DASHES)], "width": 2.4},
                )
            )
        if group[x_axis].notna().any():
            fig.add_vline(x=group[x_axis].median(), line_dash="dot", line_color="#94a3b8", opacity=0.55)
        if group[y_axis].notna().any():
            fig.add_hline(y=group[y_axis].median(), line_dash="dot", line_color="#94a3b8", opacity=0.55)
        chart_title = title if df["group_label"].nunique() == 1 else f"{title}: {group_label}"
        fig.update_layout(
            title=chart_title,
            xaxis_title=_axis_label(x_axis),
            yaxis_title=_axis_label(y_axis),
            hovermode="closest",
        )
        figures.append(_apply_report_layout(fig, height=560))
    return figures


def build_climatogram_report_figures(
    items: list[dict[str, Any]],
    chart_type: str,
    x_axis: str,
    y_axis: str,
    connect_months: bool,
    close_polygon: bool,
    show_labels: bool,
    overlay_stations: bool,
    overlay_periods: bool,
    color_map: dict[Any, str] | None = None,
) -> list[go.Figure]:
    """Выбирает renderer климатограммы по текущему типу графика.

    Args:
        items: Результаты климатограмм.
        chart_type: Тип графика `classic` или `scatter`.
        x_axis: Ключ оси X для точечной климатограммы.
        y_axis: Ключ оси Y для точечной климатограммы.
        connect_months: Соединять ли месяцы.
        close_polygon: Замыкать ли линию.
        show_labels: Подписывать ли точки.
        overlay_stations: Накладывать ли станции.
        overlay_periods: Накладывать ли периоды.
        color_map: Цветовая карта.

    Returns:
        Список Plotly-фигур для PDF.
    """

    if chart_type == "scatter":
        return build_climatogram_scatter_figures(
            items,
            overlay_stations=overlay_stations,
            overlay_periods=overlay_periods,
            x_axis=x_axis,
            y_axis=y_axis,
            connect_months=connect_months,
            close_polygon=close_polygon,
            show_labels=show_labels,
            color_map=color_map,
        )
    return build_climatogram_figures(
        items,
        overlay_stations=overlay_stations,
        overlay_periods=overlay_periods,
        color_map=color_map,
    )


def build_forecast_figure(payload: Any, title: str = "Прогнозные значения") -> go.Figure:
    """Строит фигуру прогноза.

    Args:
        payload: JSON результата прогнозирования.
        title: Заголовок графика.

    Returns:
        Plotly-фигура прогноза.
    """

    if isinstance(payload, dict):
        payload = payload.get("forecast") or payload.get("values") or payload
    return build_timeseries_figure(payload, title=title)

