"""Metric card components."""

from __future__ import annotations

from typing import Any

import streamlit as st

from klimatika_frontend.utils.formatters import format_metric_label, format_number


def render_metric_cards(metrics: dict[str, Any] | None, columns: int = 4) -> None:
    if not isinstance(metrics, dict) or not metrics:
        st.info("Метрики в ответе backend отсутствуют.")
        return

    items = [(key, value) for key, value in metrics.items() if key != "status" and not isinstance(value, (dict, list))]
    if not items:
        st.dataframe(metrics, use_container_width=True)
        return

    cols = st.columns(min(columns, max(len(items), 1)))
    for index, (key, value) in enumerate(items):
        with cols[index % len(cols)]:
            st.metric(format_metric_label(key), format_number(value) if isinstance(value, (int, float)) else str(value))
