"""API and method error renderers."""

from __future__ import annotations

from typing import Any

import streamlit as st

from klimatika_frontend.api.client import ApiError
from klimatika_frontend.state.session import clear_auth_state


ERROR_HINTS = {
    "UNAUTHORIZED": "Сессия истекла. Войдите снова.",
    "FORBIDDEN": "У вас нет доступа к этому ресурсу.",
    "STATION_NOT_FOUND": "Выбранная станция недоступна.",
    "PARAMETER_NOT_FOUND": "Выбранный параметр недоступен.",
    "OBSERVATIONS_NOT_FOUND": "За выбранный период наблюдений нет.",
    "NOT_ENOUGH_DATA": "Выбранный ряд слишком короткий для этого анализа.",
    "INVALID_PERIOD": "Проверьте даты периода.",
    "INVALID_AGGREGATION": "Выберите поддерживаемую агрегацию.",
    "INVALID_ANALYSIS_METHOD": "Один из методов анализа не поддерживается backend.",
    "ANALYSIS_FAILED": "Backend не смог выполнить анализ.",
    "REPORT_FAILED": "Backend не смог сформировать отчёт.",
    "CONNECTION_ERROR": "Backend API сейчас недоступен.",
    "TIMEOUT": "Backend слишком долго отвечает.",
}


def render_api_error(error: Exception | ApiError) -> None:
    """Отображает ошибку API в пользовательском виде.

    Args:
        error: Исключение API или неожиданная ошибка.

    Returns:
        None.
    """

    if isinstance(error, ApiError):
        if error.status_code == 401 or error.code == "UNAUTHORIZED":
            clear_auth_state()
        hint = ERROR_HINTS.get(error.code or "", error.message)
        st.error(hint)
        if error.message and error.message != hint:
            st.caption(error.message)
        with st.expander("Технические детали", expanded=False):
            st.json(
                {
                    "status_code": error.status_code,
                    "code": error.code,
                    "message": error.message,
                    "context": error.context,
                    "raw": error.raw,
                }
            )
        return

    st.error("Произошла непредвиденная ошибка.")
    with st.expander("Технические детали", expanded=False):
        st.write(str(error))


def render_method_errors(results: dict[str, Any] | None) -> None:
    """Отображает ошибки отдельных методов анализа.

    Args:
        results: JSON-словарь результатов анализа по методам.

    Returns:
        None.
    """

    if not isinstance(results, dict):
        return
    failed = []
    for method, payload in results.items():
        if isinstance(payload, dict) and payload.get("status") == "failed":
            failed.append((method, payload))
    if not failed:
        return
    st.warning("Часть методов анализа завершилась с ошибкой.")
    for method, payload in failed:
        message = payload.get("message") or payload.get("error") or "Метод не выполнен."
        with st.expander(f"{method}: {message}", expanded=False):
            st.json(payload)

