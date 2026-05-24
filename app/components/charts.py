"""Plotly chart helpers."""

from __future__ import annotations

import re
from typing import Any

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from app.utils.formatters import series_dataframe, unwrap_records


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
CLIMATOGRAM_AXIS_ALIASES = {
    "temperature_mean": ("temperature_mean", "temperature", "tavg_norm_1995_2024"),
    "precipitation_sum": ("precipitation_sum", "precipitation", "prcp_norm_1995_2024"),
}
CLIMATOGRAM_AXIS_LABELS = {
    "temperature_mean": "Температура, °C",
    "precipitation_sum": "Осадки, мм",
    "temperature": "Температура, °C",
    "precipitation": "Осадки, мм",
    "tavg_norm_1995_2024": "Средняя температура 1995-2024, °C",
    "prcp_norm_1995_2024": "Средняя сумма осадков 1995-2024, мм",
}
CLIMATOGRAM_METADATA_COLUMNS = {
    "station_id",
    "station_name",
    "period_index",
    "period_label",
    "month",
    "month_label",
    "month_sequence_label",
    "month_order",
}
MONTH_NAME_TO_NUMBER = {
    "янв": 1,
    "январь": 1,
    "фев": 2,
    "февраль": 2,
    "мар": 3,
    "март": 3,
    "апр": 4,
    "апрель": 4,
    "май": 5,
    "июн": 6,
    "июнь": 6,
    "июл": 7,
    "июль": 7,
    "авг": 8,
    "август": 8,
    "сен": 9,
    "сентябрь": 9,
    "окт": 10,
    "октябрь": 10,
    "ноя": 11,
    "ноябрь": 11,
    "дек": 12,
    "декабрь": 12,
    "jan": 1,
    "january": 1,
    "feb": 2,
    "february": 2,
    "mar": 3,
    "march": 3,
    "apr": 4,
    "april": 4,
    "may": 5,
    "jun": 6,
    "june": 6,
    "jul": 7,
    "july": 7,
    "aug": 8,
    "august": 8,
    "sep": 9,
    "september": 9,
    "oct": 10,
    "october": 10,
    "nov": 11,
    "november": 11,
    "dec": 12,
    "december": 12,
}


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


def _first_available_value(record: dict[str, Any], keys: tuple[str, ...]) -> Any:
    """Возвращает первое непустое значение из записи по списку ключей.

    Args:
        record: Месячная запись климатограммы.
        keys: Приоритетный список ключей.

    Returns:
        Первое найденное значение или None.
    """

    for key in keys:
        value = record.get(key)
        if value is not None:
            return value
    return None


def _month_number(value: Any) -> int | None:
    """Определяет номер месяца по числу или текстовому названию.

    Args:
        value: Значение месяца из backend JSON.

    Returns:
        Номер месяца от 1 до 12 или None.
    """

    try:
        number = int(value)
    except (TypeError, ValueError):
        normalized = str(value or "").strip().lower().replace(".", "")
        number = MONTH_NAME_TO_NUMBER.get(normalized)
    if number and 1 <= number <= 12:
        return number
    return None


def _month_order(value: Any) -> int:
    """Возвращает порядок месяца для сортировки годового хода.

    Args:
        value: Значение месяца из backend JSON.

    Returns:
        Порядковый номер месяца или 99 для неизвестного значения.
    """

    return _month_number(value) or 99


def _month_label(value: Any) -> str:
    """Формирует короткую подпись месяца.

    Args:
        value: Значение месяца из backend JSON.

    Returns:
        Название месяца или исходное значение в виде строки.
    """

    number = _month_number(value)
    if number:
        return MONTH_LABELS[number - 1]
    return str(value)


def _month_sequence_label(value: Any) -> str:
    """Формирует подпись месяца с календарным номером.

    Args:
        value: Значение месяца из backend JSON.

    Returns:
        Подпись вида `01 Янв` или исходное значение, если месяц неизвестен.
    """

    number = _month_number(value)
    if number:
        return f"{number:02d} {MONTH_LABELS[number - 1]}"
    return str(value)


def _axis_label(axis_key: str) -> str:
    """Возвращает человекочитаемую подпись оси климатограммы.

    Args:
        axis_key: Ключ поля месячной записи.

    Returns:
        Подпись оси для графика и selectbox.
    """

    return CLIMATOGRAM_AXIS_LABELS.get(axis_key, axis_key)


def _is_numeric_series(series: pd.Series) -> bool:
    """Проверяет, есть ли в серии хотя бы одно числовое значение.

    Args:
        series: Серия DataFrame.

    Returns:
        True, если серия может использоваться как числовая ось.
    """

    return pd.to_numeric(series, errors="coerce").notna().any()


def _hex_to_rgba(color: str, alpha: float) -> str:
    """Преобразует hex-цвет в строку rgba для заливки графика.

    Args:
        color: Цвет в формате `#RRGGBB`.
        alpha: Прозрачность от 0 до 1.

    Returns:
        Цвет в формате CSS rgba или исходный цвет, если формат неизвестен.
    """

    if not isinstance(color, str) or not re.fullmatch(r"#[0-9a-fA-F]{6}", color):
        return color
    red = int(color[1:3], 16)
    green = int(color[3:5], 16)
    blue = int(color[5:7], 16)
    return f"rgba({red}, {green}, {blue}, {alpha})"


def _closed_month_trace(trace: pd.DataFrame) -> pd.DataFrame:
    """Замыкает годовой ход последней строкой на январь.

    Args:
        trace: Месячные точки одной серии, отсортированные по календарю.

    Returns:
        DataFrame с добавленной первой строкой в конец, если это возможно.
    """

    if trace.empty or trace.iloc[0].get("month_order") != 1:
        return trace
    return pd.concat([trace, trace.iloc[[0]]], ignore_index=True)


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


def _records_from_keys(payload: Any, keys: tuple[str, ...]) -> list[dict]:
    """Извлекает список записей по одному из ключей JSON.

    Args:
        payload: JSON-ответ backend или sample API.
        keys: Допустимые ключи коллекции.

    Returns:
        Список словарей или пустой список.
    """

    if isinstance(payload, list):
        return [item for item in payload if isinstance(item, dict)]
    if not isinstance(payload, dict):
        return []
    for key in keys:
        value = payload.get(key)
        if isinstance(value, list):
            return [item for item in value if isinstance(item, dict)]
        if isinstance(value, dict):
            nested = unwrap_records(value, ("values", "series", "data", "items", "records"))
            if nested:
                return nested
    return []


def render_anomaly_chart(series_payload: Any, anomalies_payload: Any, title: str = "Аномалии") -> None:
    """Отображает график климатических аномалий относительно нулевой линии.

    Args:
        series_payload: Исходный временной ряд, сохранён для совместимости.
        anomalies_payload: JSON результата метода `anomalies`.
        title: Заголовок графика.

    Returns:
        None.
    """

    df = series_dataframe(anomalies_payload)
    if df.empty or not {"date", "value"}.issubset(df.columns):
        st.info("Аномалии отсутствуют в результате анализа.")
        return

    colors = ["#0d64d8" if value >= 0 else "#07111f" for value in df["value"]]
    fig = go.Figure()
    fig.add_trace(go.Bar(x=df["date"], y=df["value"], name="Аномалия", marker_color=colors, opacity=0.82))
    fig.add_hline(y=0, line_dash="dash", line_color="#64748b")
    fig.update_layout(title=title, xaxis_title="Дата", yaxis_title="Отклонение", hovermode="x unified", height=430)
    st.plotly_chart(fig, use_container_width=True)


def render_decomposition_chart(payload: Any, title: str = "Сезонная декомпозиция") -> None:
    """Отображает компоненты сезонной декомпозиции временного ряда.

    Args:
        payload: JSON результата метода `seasonal_decomposition`.
        title: Заголовок блока графиков.

    Returns:
        None.
    """

    if not isinstance(payload, dict) or payload.get("status") == "failed":
        st.info("Сезонная декомпозиция отсутствует или завершилась с ошибкой.")
        return

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
                y=df["value"],
                name=component_label,
                mode="lines",
                line={"color": CHART_PALETTE[index % len(CHART_PALETTE)]},
            )
        )
        has_data = True

    if not has_data:
        st.info("Backend не вернул компоненты декомпозиции.")
        return

    fig.update_layout(title=title, xaxis_title="Дата", yaxis_title="Значение", hovermode="x unified", height=480)
    st.plotly_chart(fig, use_container_width=True)


def render_extremes_chart(series_payload: Any, extremes_payload: Any, title: str = "Экстремальные значения") -> None:
    """Отображает временной ряд с отмеченными экстремальными значениями.

    Args:
        series_payload: Исходный временной ряд.
        extremes_payload: JSON результата метода `extremes`.
        title: Заголовок графика.

    Returns:
        None.
    """

    base_df = series_dataframe(series_payload)
    values_df = pd.DataFrame(_records_from_keys(extremes_payload, ("values", "points", "data", "items")))
    if base_df.empty or not {"date", "value"}.issubset(base_df.columns):
        base_df = values_df
    if base_df.empty or not {"date", "value"}.issubset(base_df.columns):
        st.info("Данные для графика экстремумов отсутствуют.")
        return

    fig = go.Figure()
    fig.add_trace(go.Scatter(x=base_df["date"], y=base_df["value"], name="Временной ряд", mode="lines", line={"color": DEFAULT_CHART_COLOR}))

    if not values_df.empty and {"date", "value", "kind"}.issubset(values_df.columns):
        high_df = values_df[values_df["kind"] == "high"]
        low_df = values_df[values_df["kind"] == "low"]
    else:
        high_df = pd.DataFrame(_records_from_keys(extremes_payload, ("maxima", "maximums", "high_extremes")))
        low_df = pd.DataFrame(_records_from_keys(extremes_payload, ("minima", "minimums", "low_extremes")))

    if not high_df.empty and {"date", "value"}.issubset(high_df.columns):
        fig.add_trace(go.Scatter(x=high_df["date"], y=high_df["value"], name="Высокие экстремумы", mode="markers", marker={"size": 11, "color": "#17b6d6"}))
    if not low_df.empty and {"date", "value"}.issubset(low_df.columns):
        fig.add_trace(go.Scatter(x=low_df["date"], y=low_df["value"], name="Низкие экстремумы", mode="markers", marker={"size": 11, "color": "#07111f"}))

    thresholds = extremes_payload.get("thresholds") if isinstance(extremes_payload, dict) else {}
    if isinstance(thresholds, dict):
        if thresholds.get("p95") is not None:
            fig.add_hline(y=thresholds["p95"], line_dash="dash", line_color="#17b6d6", annotation_text="p95")
        if thresholds.get("p05") is not None:
            fig.add_hline(y=thresholds["p05"], line_dash="dash", line_color="#07111f", annotation_text="p05")

    fig.update_layout(title=title, xaxis_title="Дата", yaxis_title="Значение", hovermode="x unified", height=480)
    st.plotly_chart(fig, use_container_width=True)


def render_correlation_heatmap(payload: Any, title: str = "Корреляционная матрица") -> None:
    """Отображает heatmap корреляционной матрицы.

    Args:
        payload: JSON результата корреляционного анализа.
        title: Заголовок графика.

    Returns:
        None.
    """

    if not isinstance(payload, dict):
        st.info("Корреляционная матрица отсутствует.")
        return

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
        st.info("Backend не вернул матрицу корреляций.")
        return

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
            hovertemplate="%{y} × %{x}: %{z:.3f}<extra></extra>",
        )
    )
    fig.update_layout(title=title, height=520)
    st.plotly_chart(fig, use_container_width=True)


def render_correlation_scatter(payload: Any, title: str = "Диаграммы корреляций") -> None:
    """Отображает scatter-графики пар параметров.

    Args:
        payload: JSON результата корреляционного анализа.
        title: Заголовок блока.

    Returns:
        None.
    """

    pairs = _records_from_keys(payload, ("pairs", "results", "data", "items"))
    if not pairs:
        st.info("Пары параметров для scatter-графиков отсутствуют.")
        return

    st.subheader(title)
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
                x=points["x"],
                y=points["y"],
                name="Наблюдения",
                mode="markers",
                marker={"size": 9, "color": DEFAULT_CHART_COLOR, "opacity": 0.72},
                text=points["date"] if "date" in points.columns else None,
            )
        )
        fig.update_layout(
            title=f"{x_name} × {y_name}" + (f" · r={correlation}" if correlation is not None else ""),
            xaxis_title=str(x_name),
            yaxis_title=str(y_name),
            height=430,
        )
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
    temp_col = next((column for column in CLIMATOGRAM_AXIS_ALIASES["temperature_mean"] if column in df.columns), "temperature_mean")
    precip_col = next((column for column in CLIMATOGRAM_AXIS_ALIASES["precipitation_sum"] if column in df.columns), "precipitation_sum")
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


def climatogram_records_dataframe(items: list[dict[str, Any]]) -> pd.DataFrame:
    """Преобразует несколько климатограмм в плоский DataFrame.

    Args:
        items: Список результатов с данными станции, периода и JSON климатограммы.

    Returns:
        DataFrame с месячными значениями, служебными полями и исходными числовыми колонками.
    """

    records: list[dict[str, Any]] = []
    for item in items:
        months = unwrap_records(item.get("result"), ("months", "values", "data", "items"))
        for month in months:
            month_value = month.get("month")
            row = {
                "station_id": item.get("station_id"),
                "station_name": item.get("station_name") or item.get("station_label") or "Станция",
                "period_index": item.get("period_index"),
                "period_label": item.get("period_label") or "Период",
                "month": month_value,
                "month_label": _month_label(month_value),
                "month_sequence_label": _month_sequence_label(month_value),
                "month_order": _month_order(month_value),
                "temperature_mean": _first_available_value(month, CLIMATOGRAM_AXIS_ALIASES["temperature_mean"]),
                "precipitation_sum": _first_available_value(month, CLIMATOGRAM_AXIS_ALIASES["precipitation_sum"]),
            }
            for key, value in month.items():
                if key not in row:
                    row[key] = value
            records.append(row)
    return pd.DataFrame(records)


def climatogram_axis_options(items: list[dict[str, Any]]) -> list[tuple[str, str]]:
    """Возвращает доступные числовые оси для точечной климатограммы.

    Args:
        items: Результаты климатограмм.

    Returns:
        Список пар `ключ поля`, `подпись`.
    """

    options = [("temperature_mean", _axis_label("temperature_mean")), ("precipitation_sum", _axis_label("precipitation_sum"))]
    seen = {key for key, _ in options}
    alias_columns = {alias for aliases in CLIMATOGRAM_AXIS_ALIASES.values() for alias in aliases}
    df = climatogram_records_dataframe(items)
    if df.empty:
        return options

    for column in df.columns:
        if column in seen or column in CLIMATOGRAM_METADATA_COLUMNS or column in alias_columns:
            continue
        if _is_numeric_series(df[column]):
            options.append((str(column), _axis_label(str(column))))
            seen.add(str(column))
    return options


def climatogram_scatter_dataframe(items: list[dict[str, Any]], x_axis: str, y_axis: str) -> pd.DataFrame:
    """Подготавливает данные для точечной климатограммы.

    Args:
        items: Результаты климатограмм.
        x_axis: Ключ поля для горизонтальной оси.
        y_axis: Ключ поля для вертикальной оси.

    Returns:
        DataFrame без строк, где отсутствуют выбранные значения X или Y.
    """

    df = climatogram_records_dataframe(items)
    if df.empty or x_axis not in df.columns or y_axis not in df.columns:
        return pd.DataFrame()

    df = df.copy()
    df[x_axis] = pd.to_numeric(df[x_axis], errors="coerce")
    df[y_axis] = pd.to_numeric(df[y_axis], errors="coerce")
    return df.dropna(subset=[x_axis, y_axis]).sort_values(["station_name", "period_index", "month_order"])


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

    df = climatogram_records_dataframe(items)
    if df.empty:
        st.info("Данные климатограмм отсутствуют.")
        return

    required_columns = {"month", "temperature_mean", "precipitation_sum"}
    if (
        not required_columns.issubset(df.columns)
        or df["temperature_mean"].isna().all()
        or df["precipitation_sum"].isna().all()
    ):
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


def render_multi_climatogram_scatter(
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
) -> None:
    """Отображает точечные климатограммы для станций и периодов.

    Args:
        items: Список результатов с данными станции, периода и JSON климатограммы.
        overlay_stations: Накладывать метеостанции на один график внутри периода.
        overlay_periods: Накладывать периоды на один график внутри станции.
        x_axis: Ключ поля для горизонтальной оси.
        y_axis: Ключ поля для вертикальной оси.
        connect_months: Соединять ли месяцы линией от января к декабрю.
        close_polygon: Замыкать ли линию из декабря обратно в январь и заливать область.
        show_labels: Подписывать ли точки месяцами.
        title: Заголовок графика.
        color_map: Цвета по ключам станции и показателя.

    Returns:
        None.
    """

    df = climatogram_scatter_dataframe(items, x_axis, y_axis)
    if df.empty:
        st.info("Данные для точечной климатограммы отсутствуют или не содержат выбранные оси.")
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
                        line={
                            "color": color,
                            "dash": LINE_DASHES[trace_index % len(LINE_DASHES)],
                            "width": 2.8,
                        },
                    )
                )
            mode = "lines+markers" if connect_months else "markers"
            if connect_months and close_polygon:
                mode = "markers"
            if show_labels:
                mode = f"{mode}+text"
            text_values = trace["month_sequence_label"].tolist() if show_labels else None
            fig.add_trace(
                go.Scatter(
                    x=trace[x_axis],
                    y=trace[y_axis],
                    name=str(trace_label),
                    mode=mode,
                    text=text_values,
                    textposition="top center",
                    customdata=trace[["station_name", "period_label", "month_sequence_label"]].to_numpy(),
                    marker={"size": 12, "color": color, "line": {"color": "#f8fbff", "width": 1.4}},
                    line={"color": color, "dash": LINE_DASHES[trace_index % len(LINE_DASHES)], "width": 2.4},
                    hovertemplate=(
                        "<b>%{customdata[0]}</b><br>"
                        "%{customdata[1]}<br>"
                        "Месяц: %{customdata[2]}<br>"
                        f"{_axis_label(x_axis)}: %{{x:.2f}}<br>"
                        f"{_axis_label(y_axis)}: %{{y:.2f}}"
                        "<extra></extra>"
                    ),
                )
            )
            first_month = trace[trace["month_order"] == 1]
            last_month = trace[trace["month_order"] == 12]
            if not first_month.empty:
                fig.add_trace(
                    go.Scatter(
                        x=first_month[x_axis],
                        y=first_month[y_axis],
                        name=f"Начало года · {trace_label}",
                        mode="markers",
                        showlegend=False,
                        marker={
                            "size": 17,
                            "symbol": "circle-open",
                            "color": color,
                            "line": {"color": "#07111f", "width": 3},
                        },
                        hoverinfo="skip",
                    )
                )
            if not last_month.empty:
                fig.add_trace(
                    go.Scatter(
                        x=last_month[x_axis],
                        y=last_month[y_axis],
                        name=f"Конец года · {trace_label}",
                        mode="markers",
                        showlegend=False,
                        marker={
                            "size": 17,
                            "symbol": "diamond-open",
                            "color": color,
                            "line": {"color": "#17b6d6", "width": 3},
                        },
                        hoverinfo="skip",
                    )
                )

        if group[x_axis].notna().any():
            fig.add_vline(x=group[x_axis].median(), line_dash="dot", line_color="#94a3b8", opacity=0.55)
        if group[y_axis].notna().any():
            fig.add_hline(y=group[y_axis].median(), line_dash="dot", line_color="#94a3b8", opacity=0.55)

        chart_title = title if len(group_labels) == 1 else f"{title}: {group_label}"
        fig.update_layout(
            title=chart_title,
            xaxis_title=_axis_label(x_axis),
            yaxis_title=_axis_label(y_axis),
            hovermode="closest",
            height=520,
        )
        fig.add_annotation(
            text=(
                "Годовой ход соединяется в календарном порядке: 01 Янв -> 12 Дек -> 01 Янв."
                if close_polygon and connect_months
                else "Годовой ход соединяется в календарном порядке: 01 Янв -> 12 Дек."
            ),
            xref="paper",
            yref="paper",
            x=0,
            y=1.08,
            showarrow=False,
            align="left",
            font={"size": 12, "color": "#475569"},
        )
        st.plotly_chart(fig, use_container_width=True)
