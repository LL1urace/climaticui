"""PDF generation for KlimatikA frontend reports."""

from __future__ import annotations

import io
import subprocess
import sys
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Any, Mapping

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.graphics.shapes import Circle, Drawing, Line, Polygon, PolyLine, Rect, String
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (
    Image,
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table as PdfTable,
    TableStyle,
)

from app.reports.sections import ReportBlock, ReportSection, build_report_blocks


FONT_REGULAR = "KlimatikaRegular"
FONT_BOLD = "KlimatikaBold"
FALLBACK_FONT = "Helvetica"
FALLBACK_BOLD = "Helvetica-Bold"
MAX_TABLE_ROWS = 42
MAX_TABLE_COLUMNS = 8
MAX_REPORT_FIGURES = 12
FIGURE_EXPORT_TIMEOUT_SECONDS = 18
FALLBACK_CHART_WIDTH = 17.2 * cm
FALLBACK_CHART_HEIGHT = 10.25 * cm
FALLBACK_PALETTE = ["#0d64d8", "#17b6d6", "#07111f", "#f59e0b", "#16a34a", "#dc2626"]


def _font_candidates() -> tuple[list[Path], list[Path]]:
    """Возвращает возможные пути к шрифтам с кириллицей.

    Returns:
        Кортеж списков путей для обычного и жирного начертания.
    """

    regular = [
        Path("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"),
        Path("C:/Windows/Fonts/arial.ttf"),
        Path("C:/Windows/Fonts/dejavusans.ttf"),
    ]
    bold = [
        Path("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"),
        Path("C:/Windows/Fonts/arialbd.ttf"),
        Path("C:/Windows/Fonts/dejavusans-bold.ttf"),
    ]
    return regular, bold


def _first_existing(paths: list[Path]) -> Path | None:
    """Возвращает первый существующий путь из списка.

    Args:
        paths: Кандидаты путей.

    Returns:
        Найденный путь или None.
    """

    for path in paths:
        if path.exists():
            return path
    return None


def _register_fonts() -> tuple[str, str]:
    """Регистрирует шрифты для PDF и возвращает имена семейств.

    Returns:
        Имена обычного и жирного шрифта ReportLab.
    """

    regular_candidates, bold_candidates = _font_candidates()
    regular_path = _first_existing(regular_candidates)
    bold_path = _first_existing(bold_candidates)
    if not regular_path:
        return FALLBACK_FONT, FALLBACK_BOLD

    if FONT_REGULAR not in pdfmetrics.getRegisteredFontNames():
        pdfmetrics.registerFont(TTFont(FONT_REGULAR, str(regular_path)))
    if bold_path and FONT_BOLD not in pdfmetrics.getRegisteredFontNames():
        pdfmetrics.registerFont(TTFont(FONT_BOLD, str(bold_path)))
    return FONT_REGULAR, FONT_BOLD if bold_path else FONT_REGULAR


def _styles() -> dict[str, ParagraphStyle]:
    """Создаёт стили абзацев для PDF.

    Returns:
        Словарь стилей ReportLab.
    """

    font_name, bold_name = _register_fonts()
    base = getSampleStyleSheet()
    return {
        "title": ParagraphStyle(
            "KlimatikaTitle",
            parent=base["Title"],
            fontName=bold_name,
            fontSize=27,
            leading=32,
            textColor=colors.HexColor("#07111f"),
            alignment=TA_LEFT,
            spaceAfter=16,
        ),
        "subtitle": ParagraphStyle(
            "KlimatikaSubtitle",
            parent=base["BodyText"],
            fontName=font_name,
            fontSize=12,
            leading=17,
            textColor=colors.HexColor("#475569"),
            spaceAfter=12,
        ),
        "h1": ParagraphStyle(
            "KlimatikaHeading",
            parent=base["Heading1"],
            fontName=bold_name,
            fontSize=20,
            leading=25,
            textColor=colors.HexColor("#0d64d8"),
            spaceBefore=8,
            spaceAfter=9,
        ),
        "h2": ParagraphStyle(
            "KlimatikaTableHeading",
            parent=base["Heading2"],
            fontName=bold_name,
            fontSize=13,
            leading=17,
            textColor=colors.HexColor("#07111f"),
            spaceBefore=8,
            spaceAfter=6,
        ),
        "body": ParagraphStyle(
            "KlimatikaBody",
            parent=base["BodyText"],
            fontName=font_name,
            fontSize=10,
            leading=14,
            textColor=colors.HexColor("#07111f"),
            spaceAfter=7,
        ),
        "small": ParagraphStyle(
            "KlimatikaSmall",
            parent=base["BodyText"],
            fontName=font_name,
            fontSize=8,
            leading=10,
            textColor=colors.HexColor("#475569"),
            spaceAfter=4,
        ),
        "table": ParagraphStyle(
            "KlimatikaTable",
            parent=base["BodyText"],
            fontName=font_name,
            fontSize=7,
            leading=9,
            textColor=colors.HexColor("#07111f"),
        ),
        "table_header": ParagraphStyle(
            "KlimatikaTableHeader",
            parent=base["BodyText"],
            fontName=bold_name,
            fontSize=7,
            leading=9,
            textColor=colors.white,
            alignment=TA_CENTER,
        ),
    }


def _safe_text(value: Any) -> str:
    """Преобразует значение в безопасный текст для PDF.

    Args:
        value: Любое значение таблицы или подписи.

    Returns:
        Экранированная строка.
    """

    if value is None:
        return ""
    text = str(value)
    return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def _plain_text(value: Any, max_length: int = 46) -> str:
    """Преобразует значение в короткий обычный текст для Drawing.

    Args:
        value: Исходное значение.
        max_length: Максимальная длина строки.

    Returns:
        Короткая строка без HTML-экранирования.
    """

    if value is None:
        return ""
    text = str(value)
    return text if len(text) <= max_length else f"{text[: max_length - 1]}..."


def _as_list(value: Any) -> list[Any]:
    """Преобразует Plotly-массив в обычный список.

    Args:
        value: Список, tuple, pandas/numpy series или скаляр.

    Returns:
        Обычный список значений.
    """

    if value is None:
        return []
    if hasattr(value, "tolist"):
        converted = value.tolist()
        return converted if isinstance(converted, list) else [converted]
    if isinstance(value, (list, tuple)):
        return list(value)
    return [value]


def _to_float(value: Any) -> float | None:
    """Преобразует значение графика в float.

    Args:
        value: Значение оси или метрики.

    Returns:
        Число или None.
    """

    try:
        if value in (None, ""):
            return None
        return float(value)
    except (TypeError, ValueError):
        return None


def _hex_color(value: Any, fallback: str = "#0d64d8") -> colors.Color:
    """Возвращает цвет ReportLab из hex-строки.

    Args:
        value: Цвет из Plotly trace.
        fallback: Цвет по умолчанию.

    Returns:
        Цвет ReportLab.
    """

    if isinstance(value, str) and value.startswith("#") and len(value) == 7:
        return colors.HexColor(value)
    return colors.HexColor(fallback)


def _trace_color(trace: dict[str, Any], index: int) -> colors.Color:
    """Определяет цвет trace для fallback-графика.

    Args:
        trace: Plotly trace в JSON-формате.
        index: Порядковый номер trace.

    Returns:
        Цвет ReportLab.
    """

    line = trace.get("line") if isinstance(trace.get("line"), dict) else {}
    marker = trace.get("marker") if isinstance(trace.get("marker"), dict) else {}
    color = line.get("color") or marker.get("color") or FALLBACK_PALETTE[index % len(FALLBACK_PALETTE)]
    if isinstance(color, list):
        color = color[0] if color else None
    return _hex_color(color, FALLBACK_PALETTE[index % len(FALLBACK_PALETTE)])


def _axis_range(values: list[float]) -> tuple[float, float]:
    """Возвращает диапазон оси с небольшим отступом.

    Args:
        values: Числовые значения оси.

    Returns:
        Пара минимум/максимум.
    """

    if not values:
        return 0.0, 1.0
    minimum = min(values)
    maximum = max(values)
    if minimum == maximum:
        padding = abs(minimum) * 0.1 or 1.0
        return minimum - padding, maximum + padding
    padding = (maximum - minimum) * 0.08
    return minimum - padding, maximum + padding


def _short_tick(value: Any) -> str:
    """Форматирует подпись деления оси.

    Args:
        value: Значение деления.

    Returns:
        Короткая подпись.
    """

    numeric = _to_float(value)
    if numeric is not None:
        return f"{numeric:.2f}".rstrip("0").rstrip(".")
    return _plain_text(value, 12)


def _layout_title(fig_json: dict[str, Any], default: str = "График") -> str:
    """Извлекает заголовок Plotly-фигуры.

    Args:
        fig_json: JSON-представление Plotly-фигуры.
        default: Заголовок по умолчанию.

    Returns:
        Текст заголовка.
    """

    title = fig_json.get("layout", {}).get("title")
    if isinstance(title, dict):
        return _plain_text(title.get("text") or default, 80)
    return _plain_text(title or default, 80)


def _table_columns(rows: list[dict[str, Any]]) -> list[str]:
    """Выбирает видимые колонки таблицы.

    Args:
        rows: Строки таблицы.

    Returns:
        Список колонок, ограниченный по ширине PDF.
    """

    columns: list[str] = []
    for row in rows:
        for key in row:
            if key not in columns:
                columns.append(str(key))
            if len(columns) >= MAX_TABLE_COLUMNS:
                return columns
    return columns


def _table_flowables(report_table: Any, styles: dict[str, ParagraphStyle]) -> list[Any]:
    """Преобразует таблицу отчёта в элементы ReportLab.

    Args:
        report_table: Табличный блок отчёта.
        styles: Стили абзацев.

    Returns:
        Список flowable-элементов PDF.
    """

    rows = report_table.rows or []
    if not rows:
        return []
    visible_rows = rows[:MAX_TABLE_ROWS]
    columns = _table_columns(visible_rows)
    if not columns:
        return []

    data = [[Paragraph(_safe_text(column), styles["table_header"]) for column in columns]]
    for row in visible_rows:
        data.append([Paragraph(_safe_text(row.get(column)), styles["table"]) for column in columns])

    table = PdfTable(data, repeatRows=1, hAlign="LEFT")
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#07111f")),
                ("GRID", (0, 0), (-1, -1), 0.35, colors.HexColor("#d7e2f2")),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f4f8ff")]),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 4),
                ("RIGHTPADDING", (0, 0), (-1, -1), 4),
                ("TOPPADDING", (0, 0), (-1, -1), 4),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ]
        )
    )

    flowables: list[Any] = [Paragraph(_safe_text(report_table.title), styles["h2"]), table]
    if len(rows) > MAX_TABLE_ROWS:
        flowables.append(
            Paragraph(
                f"Показаны первые {MAX_TABLE_ROWS} строк из {len(rows)}. Полная таблица доступна в интерфейсе приложения.",
                styles["small"],
            )
        )
    flowables.append(Spacer(1, 0.28 * cm))
    return flowables


def _chart_frame(title: str) -> tuple[Drawing, float, float, float, float]:
    """Создаёт базовую область fallback-графика.

    Args:
        title: Заголовок графика.

    Returns:
        Drawing и координаты plot-area: left, bottom, width, height.
    """

    font_name, bold_name = _register_fonts()
    drawing = Drawing(FALLBACK_CHART_WIDTH, FALLBACK_CHART_HEIGHT)
    drawing.add(Rect(0, 0, FALLBACK_CHART_WIDTH, FALLBACK_CHART_HEIGHT, strokeColor=colors.HexColor("#d7e2f2"), fillColor=colors.white))
    drawing.add(String(16, FALLBACK_CHART_HEIGHT - 22, _plain_text(title, 86), fontName=bold_name, fontSize=10.5, fillColor=colors.HexColor("#07111f")))
    left = 46
    bottom = 36
    width = FALLBACK_CHART_WIDTH - 66
    height = FALLBACK_CHART_HEIGHT - 74
    drawing.add(Line(left, bottom, left, bottom + height, strokeColor=colors.HexColor("#94a3b8"), strokeWidth=0.7))
    drawing.add(Line(left, bottom, left + width, bottom, strokeColor=colors.HexColor("#94a3b8"), strokeWidth=0.7))
    return drawing, left, bottom, width, height


def _draw_grid(
    drawing: Drawing,
    left: float,
    bottom: float,
    width: float,
    height: float,
    y_min: float,
    y_max: float,
) -> None:
    """Рисует сетку и подписи оси Y.

    Args:
        drawing: Drawing-график.
        left: Левая координата области.
        bottom: Нижняя координата области.
        width: Ширина области.
        height: Высота области.
        y_min: Минимум оси Y.
        y_max: Максимум оси Y.

    Returns:
        None.
    """

    font_name, _ = _register_fonts()
    for index in range(5):
        ratio = index / 4
        y = bottom + height * ratio
        value = y_min + (y_max - y_min) * ratio
        drawing.add(Line(left, y, left + width, y, strokeColor=colors.HexColor("#e2e8f0"), strokeWidth=0.45))
        drawing.add(String(6, y - 3, _short_tick(value), fontName=font_name, fontSize=6.5, fillColor=colors.HexColor("#64748b")))


def _scale(value: float, minimum: float, maximum: float, size: float, offset: float) -> float:
    """Масштабирует значение в координату Drawing.

    Args:
        value: Исходное значение.
        minimum: Минимум диапазона.
        maximum: Максимум диапазона.
        size: Размер области.
        offset: Смещение области.

    Returns:
        Координата внутри Drawing.
    """

    if maximum == minimum:
        return offset + size / 2
    return offset + ((value - minimum) / (maximum - minimum)) * size


def _fallback_xy_drawing(fig_json: dict[str, Any]) -> Drawing:
    """Рисует fallback-график для scatter/line Plotly traces.

    Args:
        fig_json: JSON-представление Plotly-фигуры.

    Returns:
        Drawing с линиями и точками.
    """

    title = _layout_title(fig_json)
    drawing, left, bottom, width, height = _chart_frame(title)
    font_name, _ = _register_fonts()
    traces = [trace for trace in fig_json.get("data", []) if trace.get("type", "scatter") in ("scatter", "scattergl")]
    prepared: list[tuple[dict[str, Any], list[float], list[float], list[Any]]] = []
    all_x: list[float] = []
    all_y: list[float] = []
    x_is_numeric = True

    for trace in traces:
        y_raw = _as_list(trace.get("y"))
        x_raw = _as_list(trace.get("x")) or list(range(len(y_raw)))
        values = []
        for item_index, y_value in enumerate(y_raw):
            y_numeric = _to_float(y_value)
            if y_numeric is None:
                continue
            x_source = x_raw[item_index] if item_index < len(x_raw) else item_index
            x_numeric = _to_float(x_source)
            if x_numeric is None:
                x_is_numeric = False
                x_numeric = float(item_index)
            values.append((x_numeric, y_numeric, x_source))
        if not values:
            continue
        x_values = [item[0] for item in values]
        y_values = [item[1] for item in values]
        labels = [item[2] for item in values]
        prepared.append((trace, x_values, y_values, labels))
        all_x.extend(x_values)
        all_y.extend(y_values)

    if not prepared:
        drawing.add(String(left + 12, bottom + height / 2, "Нет числовых данных для графика", fontName=font_name, fontSize=9, fillColor=colors.HexColor("#64748b")))
        return drawing

    x_min, x_max = _axis_range(all_x)
    y_min, y_max = _axis_range(all_y)
    _draw_grid(drawing, left, bottom, width, height, y_min, y_max)

    for trace_index, (trace, x_values, y_values, labels) in enumerate(prepared):
        color = _trace_color(trace, trace_index)
        points = []
        step = max(1, len(x_values) // 600)
        for x_value, y_value in zip(x_values[::step], y_values[::step]):
            points.extend([_scale(x_value, x_min, x_max, width, left), _scale(y_value, y_min, y_max, height, bottom)])
        if len(points) >= 4 and trace.get("fill") == "toself":
            drawing.add(Polygon(points, strokeColor=color, fillColor=colors.HexColor("#dbeafe"), strokeWidth=0.7))
        elif len(points) >= 4 and "lines" in str(trace.get("mode", "lines")):
            drawing.add(PolyLine(points, strokeColor=color, strokeWidth=1.35))
        if "markers" in str(trace.get("mode", "lines+markers")) or len(points) < 4:
            marker_step = max(1, len(x_values) // 80)
            for x_value, y_value in zip(x_values[::marker_step], y_values[::marker_step]):
                drawing.add(Circle(_scale(x_value, x_min, x_max, width, left), _scale(y_value, y_min, y_max, height, bottom), 2.1, strokeColor=color, fillColor=color))
        text_values = _as_list(trace.get("text"))
        if text_values:
            label_step = max(1, len(text_values) // 18)
            for label_index in range(0, min(len(text_values), len(x_values)), label_step):
                drawing.add(
                    String(
                        _scale(x_values[label_index], x_min, x_max, width, left) + 2,
                        _scale(y_values[label_index], y_min, y_max, height, bottom) + 4,
                        _plain_text(text_values[label_index], 8),
                        fontName=font_name,
                        fontSize=5.8,
                        fillColor=colors.HexColor("#334155"),
                    )
                )

    first_x_label = _short_tick(all_x[0] if x_is_numeric else prepared[0][3][0])
    last_x_label = _short_tick(all_x[-1] if x_is_numeric else prepared[-1][3][-1])
    drawing.add(String(left, bottom - 16, first_x_label, fontName=font_name, fontSize=6.5, fillColor=colors.HexColor("#64748b")))
    drawing.add(String(left + width - 52, bottom - 16, last_x_label, fontName=font_name, fontSize=6.5, fillColor=colors.HexColor("#64748b")))
    return drawing


def _fallback_bar_drawing(fig_json: dict[str, Any]) -> Drawing:
    """Рисует fallback-график для столбчатых Plotly traces.

    Args:
        fig_json: JSON-представление Plotly-фигуры.

    Returns:
        Drawing со столбцами.
    """

    title = _layout_title(fig_json)
    drawing, left, bottom, width, height = _chart_frame(title)
    font_name, _ = _register_fonts()
    traces = [trace for trace in fig_json.get("data", []) if trace.get("type") == "bar"]
    if not traces:
        return drawing

    orientation = traces[0].get("orientation")
    if orientation == "h":
        x_values = [_to_float(value) for value in _as_list(traces[0].get("x"))]
        y_labels = _as_list(traces[0].get("y"))
        pairs = [(label, value) for label, value in zip(y_labels, x_values) if value is not None][:14]
        if not pairs:
            return drawing
        x_min, x_max = _axis_range([0.0] + [value for _, value in pairs])
        bar_height = min(15, height / max(len(pairs), 1) * 0.68)
        gap = height / max(len(pairs), 1)
        for index, (label, value) in enumerate(pairs):
            y = bottom + height - (index + 1) * gap + (gap - bar_height) / 2
            bar_width = _scale(value, x_min, x_max, width, 0)
            color = _trace_color(traces[0], index)
            drawing.add(Rect(left, y, max(1, bar_width), bar_height, strokeColor=color, fillColor=color))
            drawing.add(String(6, y + 3, _plain_text(label, 16), fontName=font_name, fontSize=6, fillColor=colors.HexColor("#64748b")))
        return drawing

    categories: list[Any] = []
    for trace in traces:
        for label in _as_list(trace.get("x")):
            if label not in categories:
                categories.append(label)
    categories = categories[:18]
    all_values = []
    trace_values: list[list[float | None]] = []
    for trace in traces:
        values = [_to_float(value) for value in _as_list(trace.get("y"))]
        trace_values.append(values)
        all_values.extend(value for value in values if value is not None)
    y_min, y_max = _axis_range([0.0] + all_values)
    _draw_grid(drawing, left, bottom, width, height, y_min, y_max)
    group_width = width / max(len(categories), 1)
    bar_width = max(2.5, min(12, group_width / max(len(traces), 1) * 0.72))
    for trace_index, trace in enumerate(traces):
        color = _trace_color(trace, trace_index)
        x_labels = _as_list(trace.get("x"))
        values = trace_values[trace_index]
        for category_index, category in enumerate(categories):
            try:
                value_index = x_labels.index(category)
            except ValueError:
                continue
            if value_index >= len(values) or values[value_index] is None:
                continue
            value = values[value_index] or 0
            x = left + category_index * group_width + trace_index * bar_width + 3
            y0 = _scale(0, y_min, y_max, height, bottom)
            y1 = _scale(value, y_min, y_max, height, bottom)
            drawing.add(Rect(x, min(y0, y1), bar_width, max(1, abs(y1 - y0)), strokeColor=color, fillColor=color))
    label_step = max(1, len(categories) // 6)
    for index in range(0, len(categories), label_step):
        drawing.add(String(left + index * group_width, bottom - 16, _plain_text(categories[index], 9), fontName=font_name, fontSize=6, fillColor=colors.HexColor("#64748b")))
    return drawing


def _heatmap_color(value: float) -> colors.Color:
    """Возвращает цвет ячейки fallback heatmap.

    Args:
        value: Значение корреляции от -1 до 1.

    Returns:
        Цвет ReportLab.
    """

    value = max(-1.0, min(1.0, value))
    if value < 0:
        intensity = 1 + value
        return colors.Color(0.03 + 0.9 * intensity, 0.07 + 0.9 * intensity, 0.12 + 0.9 * intensity)
    intensity = value
    return colors.Color(0.97 - 0.88 * intensity, 0.98 - 0.27 * intensity, 1.0 - 0.16 * intensity)


def _fallback_heatmap_drawing(fig_json: dict[str, Any]) -> Drawing:
    """Рисует fallback heatmap для корреляционной матрицы.

    Args:
        fig_json: JSON-представление Plotly-фигуры.

    Returns:
        Drawing с матрицей.
    """

    title = _layout_title(fig_json)
    drawing, left, bottom, width, height = _chart_frame(title)
    font_name, _ = _register_fonts()
    heatmap = next((trace for trace in fig_json.get("data", []) if trace.get("type") == "heatmap"), None)
    if not heatmap:
        return drawing
    matrix = _as_list(heatmap.get("z"))
    matrix = [row for row in matrix if isinstance(row, list)]
    if not matrix:
        return drawing
    row_count = len(matrix)
    column_count = max(len(row) for row in matrix)
    cell = min(width / max(column_count, 1), height / max(row_count, 1))
    x0 = left + max(0, (width - cell * column_count) / 2)
    y0 = bottom + max(0, (height - cell * row_count) / 2)
    x_labels = _as_list(heatmap.get("x"))
    y_labels = _as_list(heatmap.get("y"))
    for row_index, row in enumerate(matrix):
        for column_index, raw_value in enumerate(row):
            value = _to_float(raw_value) or 0.0
            x = x0 + column_index * cell
            y = y0 + (row_count - row_index - 1) * cell
            drawing.add(Rect(x, y, cell, cell, strokeColor=colors.white, fillColor=_heatmap_color(value), strokeWidth=0.4))
            if cell >= 22:
                drawing.add(String(x + 4, y + cell / 2 - 3, f"{value:.2f}", fontName=font_name, fontSize=6.5, fillColor=colors.HexColor("#07111f")))
    for index, label in enumerate(x_labels[:column_count]):
        drawing.add(String(x0 + index * cell, y0 - 12, _plain_text(label, 10), fontName=font_name, fontSize=5.8, fillColor=colors.HexColor("#64748b")))
    for index, label in enumerate(y_labels[:row_count]):
        drawing.add(String(6, y0 + (row_count - index - 0.5) * cell, _plain_text(label, 14), fontName=font_name, fontSize=5.8, fillColor=colors.HexColor("#64748b")))
    return drawing


def _fallback_plotly_drawing(fig: Any) -> Drawing:
    """Создаёт упрощённый график без Kaleido.

    Args:
        fig: Plotly-фигура.

    Returns:
        Drawing, который можно напрямую вставить в PDF.
    """

    fig_json = fig.to_plotly_json()
    trace_types = {trace.get("type", "scatter") for trace in fig_json.get("data", [])}
    if "heatmap" in trace_types:
        return _fallback_heatmap_drawing(fig_json)
    if trace_types == {"bar"}:
        return _fallback_bar_drawing(fig_json)
    return _fallback_xy_drawing(fig_json)


def _plotly_figure_png_bytes(fig: Any, timeout: int = FIGURE_EXPORT_TIMEOUT_SECONDS) -> bytes:
    """Экспортирует Plotly-график в PNG через отдельный процесс.

    Args:
        fig: Plotly-фигура.
        timeout: Максимальное время экспорта в секундах.

    Returns:
        PNG-изображение в bytes.

    Raises:
        RuntimeError: Если subprocess завершился с ошибкой.
        subprocess.TimeoutExpired: Если экспорт превысил таймаут.
    """

    script = (
        "import pathlib, sys, plotly.io as pio; "
        "fig = pio.from_json(pathlib.Path(sys.argv[1]).read_text(encoding='utf-8')); "
        "png = pio.to_image(fig, format='png', width=int(sys.argv[3]), height=int(sys.argv[4]), scale=float(sys.argv[5])); "
        "pathlib.Path(sys.argv[2]).write_bytes(png)"
    )
    with tempfile.TemporaryDirectory(prefix="klimatika_pdf_") as temp_dir:
        input_path = Path(temp_dir) / "figure.json"
        output_path = Path(temp_dir) / "figure.png"
        input_path.write_text(fig.to_json(), encoding="utf-8")
        completed = subprocess.run(
            [sys.executable, "-c", script, str(input_path), str(output_path), "1040", "620", "1.25"],
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False,
        )
        if completed.returncode != 0:
            message = completed.stderr.strip() or completed.stdout.strip() or f"Код выхода {completed.returncode}"
            raise RuntimeError(message)
        return output_path.read_bytes()


def _figure_flowables(fig: Any, styles: dict[str, ParagraphStyle]) -> list[Any]:
    """Преобразует Plotly-график в PNG-изображение для PDF.

    Args:
        fig: Plotly-фигура.
        styles: Стили абзацев.

    Returns:
        Список flowable-элементов с изображением или предупреждением.

    Raises:
        RuntimeError: Не выбрасывается наружу; ошибка экспорта добавляется в PDF текстом.
    """

    try:
        png = _plotly_figure_png_bytes(fig)
    except subprocess.TimeoutExpired:
        try:
            return [
                Paragraph("График построен в упрощённом PDF-режиме.", styles["small"]),
                _fallback_plotly_drawing(fig),
                Paragraph(
                    f"Kaleido не успел подготовить изображение за {FIGURE_EXPORT_TIMEOUT_SECONDS} секунд, "
                    "поэтому использован встроенный renderer отчёта.",
                    styles["small"],
                ),
                Spacer(1, 0.35 * cm),
            ]
        except Exception as fallback_error:
            return [
                Paragraph("График не удалось экспортировать в PDF.", styles["h2"]),
                Paragraph(_safe_text(fallback_error), styles["small"]),
                Spacer(1, 0.2 * cm),
            ]
    except Exception as error:
        try:
            return [
                Paragraph("График построен в упрощённом PDF-режиме.", styles["small"]),
                _fallback_plotly_drawing(fig),
                Paragraph(
                    "Kaleido недоступен на этой системе, поэтому использован встроенный renderer отчёта.",
                    styles["small"],
                ),
                Spacer(1, 0.35 * cm),
            ]
        except Exception as fallback_error:
            return [
                Paragraph("График не удалось экспортировать в PDF.", styles["h2"]),
                Paragraph(_safe_text(f"{error}; fallback: {fallback_error}"), styles["small"]),
                Spacer(1, 0.2 * cm),
            ]

    image = Image(io.BytesIO(png), width=17.2 * cm, height=10.25 * cm)
    return [image, Spacer(1, 0.35 * cm)]


def _page_footer(canvas: Any, doc: SimpleDocTemplate) -> None:
    """Отрисовывает нижний колонтитул страницы.

    Args:
        canvas: Canvas ReportLab.
        doc: Документ ReportLab.

    Returns:
        None.
    """

    font_name, _ = _register_fonts()
    canvas.saveState()
    canvas.setFont(font_name, 8)
    canvas.setFillColor(colors.HexColor("#64748b"))
    canvas.drawString(doc.leftMargin, 1.0 * cm, "КлиматикА")
    canvas.drawRightString(A4[0] - doc.rightMargin, 1.0 * cm, f"Страница {doc.page}")
    canvas.restoreState()


def _cover_flowables(
    sections: list[ReportSection],
    state: Mapping[str, Any],
    generated_at: datetime,
    styles: dict[str, ParagraphStyle],
) -> list[Any]:
    """Создаёт титульную страницу PDF.

    Args:
        sections: Выбранные разделы отчёта.
        state: Streamlit session state или совместимый mapping.
        generated_at: Дата и время формирования.
        styles: Стили абзацев.

    Returns:
        Список элементов титульной страницы.
    """

    current_user = state.get("current_user") or {}
    user_label = current_user.get("full_name") or current_user.get("email") or "пользователь"
    section_names = ", ".join(section.title for section in sections) or "разделы не выбраны"
    return [
        Paragraph("КлиматикА", styles["title"]),
        Paragraph("PDF-отчёт по результатам анализа арктических метеостанций", styles["subtitle"]),
        Spacer(1, 0.8 * cm),
        Paragraph(f"Дата формирования: {generated_at.strftime('%d.%m.%Y %H:%M')}", styles["body"]),
        Paragraph(f"Пользователь: {_safe_text(user_label)}", styles["body"]),
        Paragraph(f"Разделы: {_safe_text(section_names)}", styles["body"]),
        Spacer(1, 1.0 * cm),
        Paragraph(
            "Отчёт сформирован во frontend из уже рассчитанных результатов текущей Streamlit-сессии. "
            "Интерактивность графиков в PDF заменена статичными изображениями.",
            styles["subtitle"],
        ),
        PageBreak(),
    ]


def _block_flowables(
    block: ReportBlock,
    styles: dict[str, ParagraphStyle],
    figure_budget: int,
) -> tuple[list[Any], int]:
    """Преобразует блок отчёта в элементы PDF.

    Args:
        block: Блок отчёта.
        styles: Стили абзацев.
        figure_budget: Оставшееся количество графиков, разрешённых для экспорта.

    Returns:
        Кортеж элементов PDF и количества использованных попыток экспорта.
    """

    flowables: list[Any] = [Paragraph(_safe_text(block.title), styles["h1"])]
    if block.description:
        flowables.append(Paragraph(_safe_text(block.description), styles["subtitle"]))
    for note in block.notes:
        flowables.append(Paragraph(_safe_text(note), styles["small"]))
    used_figures = 0
    for index, fig in enumerate(block.figures):
        if used_figures >= figure_budget:
            skipped = len(block.figures) - index
            flowables.append(
                Paragraph(
                    f"Ещё {skipped} графиков пропущено, чтобы PDF сформировался быстро. "
                    "Выберите меньше разделов или отключите лишние графики, если нужен полный набор.",
                    styles["small"],
                )
            )
            break
        flowables.extend(_figure_flowables(fig, styles))
        used_figures += 1
    for table in block.tables:
        flowables.extend(_table_flowables(table, styles))
    if not block.figures and not block.tables and not block.notes:
        flowables.append(Paragraph("Для этого раздела нет данных для включения в PDF.", styles["body"]))
    return flowables, used_figures


def build_pdf_report(
    state: Mapping[str, Any],
    selected_sections: list[ReportSection],
    include_cover: bool = True,
    include_graphs: bool = True,
    include_tables: bool = True,
    generated_at: datetime | None = None,
) -> bytes:
    """Собирает PDF-отчёт из выбранных разделов текущей сессии.

    Args:
        state: Streamlit session state или совместимый mapping.
        selected_sections: Разделы, выбранные пользователем.
        include_cover: Добавлять ли титульную страницу.
        include_graphs: Включать ли графики.
        include_tables: Включать ли таблицы.
        generated_at: Дата формирования отчёта.

    Returns:
        PDF-файл в виде bytes.
    """

    generated_at = generated_at or datetime.now()
    styles = _styles()
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        leftMargin=1.65 * cm,
        rightMargin=1.65 * cm,
        topMargin=1.45 * cm,
        bottomMargin=1.55 * cm,
        title="КлиматикА PDF-отчёт",
    )

    selected_ids = [section.id for section in selected_sections if section.available]
    blocks = build_report_blocks(
        state,
        selected_ids,
        include_graphs=include_graphs,
        include_tables=include_tables,
    )
    story: list[Any] = []
    if include_cover:
        story.extend(_cover_flowables(selected_sections, state, generated_at, styles))

    remaining_figures = MAX_REPORT_FIGURES
    for index, block in enumerate(blocks):
        if index:
            story.append(PageBreak())
        flowables, used_figures = _block_flowables(block, styles, remaining_figures)
        story.extend(flowables)
        remaining_figures = max(0, remaining_figures - used_figures)

    if not story:
        story.append(Paragraph("Нет выбранных разделов для отчёта.", styles["body"]))

    doc.build(story, onFirstPage=_page_footer, onLaterPages=_page_footer)
    return buffer.getvalue()
