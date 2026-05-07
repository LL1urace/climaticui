"""Table renderers."""

from __future__ import annotations

from typing import Any

import pandas as pd
import streamlit as st

from klimatika_frontend.utils.formatters import to_dataframe


def render_table(payload: Any, empty_message: str = "Данные для таблицы отсутствуют.") -> None:
    if isinstance(payload, pd.DataFrame):
        df = payload
    elif isinstance(payload, dict) and all(not isinstance(v, (dict, list)) for v in payload.values()):
        df = pd.DataFrame([payload])
    else:
        df = to_dataframe(payload)

    if df.empty:
        st.info(empty_message)
        return
    st.dataframe(df, use_container_width=True, hide_index=True)


def render_json_preview(payload: Any, title: str = "JSON") -> None:
    with st.expander(title, expanded=False):
        st.json(payload)

