from __future__ import annotations

import sys
from pathlib import Path

import streamlit as st

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.api import forecasts
from app.api.client import ApiError
from app.components.chart_settings import render_chart_visual_controls
from app.components.charts import render_timeseries_chart
from app.components.errors import render_api_error
from app.components.filters import common_filters, persistent_number_input, persistent_selectbox, validate_common_filters
from app.components.layout import page_title, render_home_button, setup_page
from app.components.sidebar import render_sidebar
from app.components.tables import render_json_preview, render_table
from app.state.session import init_session_state, require_auth
from app.utils.formatters import format_number


FORECAST_MODELS = {
    "linear_trend": "Линейный тренд",
    "moving_average": "Скользящее среднее",
    "seasonal_naive": "Сезонный наивный прогноз",
    "exponential_smoothing": "Экспоненциальное сглаживание",
    "trend_seasonal": "Тренд с сезонной поправкой",
    "neural_mlp": "Нейросеть MLP по лагам",
    "neural_seasonal_mlp": "Нейросеть MLP с сезонностью",
}

TRAINING_MODES = {
    "fit_selected_period": "Обучить на выбранном периоде",
    "pretrained_station": "Использовать предобучение по истории станции",
}

FORECAST_METRIC_LABELS = {
    "holdout": "Проверочный период (Holdout)",
    "mae": "Средняя абсолютная ошибка (MAE)",
    "rmse": "Среднеквадратичная ошибка (RMSE)",
    "mape": "Средняя процентная ошибка (MAPE), %",
}

FORECAST_METRIC_HELP = [
    {
        "title": "Проверочный период (Holdout)",
        "text": (
            "Последние точки ряда временно скрываются от модели. "
            "Модель обучается на более ранних данных, затем строит прогноз на скрытый участок, "
            "а приложение сравнивает прогноз с фактическими значениями."
        ),
        "how": "Например, 24 при месячной агрегации означает проверку на последних 24 месяцах.",
    },
    {
        "title": "Средняя абсолютная ошибка (MAE)",
        "text": (
            "Показывает средний размер ошибки прогноза без учёта знака. "
            "Если прогноз выше факта на 2 единицы или ниже факта на 2 единицы, ошибка в обоих случаях равна 2."
        ),
        "how": "Чем меньше MAE, тем ближе прогноз к фактическим значениям в среднем.",
    },
    {
        "title": "Среднеквадратичная ошибка (RMSE)",
        "text": (
            "Похожа на MAE, но сильнее штрафует крупные промахи. "
            "Если модель иногда резко ошибается, RMSE заметно вырастет."
        ),
        "how": "Если RMSE сильно больше MAE, значит есть отдельные большие ошибки прогноза.",
    },
    {
        "title": "Средняя процентная ошибка (MAPE)",
        "text": (
            "Показывает ошибку в процентах от фактического значения. "
            "Для температуры эта метрика часто нестабильна, потому что значения могут быть около нуля или отрицательными."
        ),
        "how": "Для температуры лучше ориентироваться на MAE и RMSE, а MAPE использовать осторожно.",
    },
]


def _render_forecast_metrics(metrics: dict) -> None:
    """Отображает метрики прогноза с русскими поясняющими названиями."""

    metric_keys = ("holdout", "mae", "rmse", "mape")
    cols = st.columns(len(metric_keys))
    for index, metric_key in enumerate(metric_keys):
        with cols[index]:
            st.metric(FORECAST_METRIC_LABELS[metric_key], format_number(metrics.get(metric_key)))


def _render_forecast_metric_help() -> None:
    """Отображает подробные пояснения метрик прогноза."""

    st.markdown("#### Как читать эти показатели")
    cols = st.columns(2)
    for index, item in enumerate(FORECAST_METRIC_HELP):
        with cols[index % 2]:
            with st.container(border=True):
                st.markdown(f"**{item['title']}**")
                st.write(item["text"])
                st.caption(item["how"])


setup_page("Прогнозирование")
init_session_state()
require_auth()
render_sidebar()
page_title("Прогнозирование", "Временный клиентский прогноз по базовым математическим моделям.")
render_home_button()
st.warning("Прогноз является исследовательским и демонстрационным; точность не гарантируется.")

with st.sidebar:
    st.subheader("Настройки отображения")
    render_chart_visual_controls(
        "forecast",
        title="График прогноза",
        caption="Стиль линии прогноза, маркеров и темы графика.",
        controls=("line", "template"),
    )

try:
    with st.container(border=True, key="forecast_parameters"):
        st.subheader("Параметры расчёта")
        filters = common_filters("forecast")
        model = persistent_selectbox(
            "Модель",
            list(FORECAST_MODELS),
            key="forecast_model",
            default="linear_trend",
            format_func=lambda item: FORECAST_MODELS[item],
        )
        training_mode = persistent_selectbox(
            "Обучение модели",
            list(TRAINING_MODES),
            key="forecast_training_mode",
            default="fit_selected_period",
            format_func=lambda item: TRAINING_MODES[item],
        )
        horizon = persistent_number_input("Горизонт", key="forecast_horizon", default=12, min_value=1, max_value=120, step=1)
        horizon_unit = persistent_selectbox(
            "Единица горизонта",
            ["days", "months", "years"],
            key="forecast_horizon_unit",
            default="months",
        )
        with st.expander("Параметры модели", expanded=False):
            model_window = persistent_number_input(
                "Окно скользящего среднего",
                key="forecast_model_window",
                default=12,
                min_value=2,
                max_value=120,
                step=1,
            )
            seasonal_period = persistent_number_input(
                "Длина сезонного цикла",
                key="forecast_seasonal_period",
                default=12,
                min_value=2,
                max_value=60,
                step=1,
            )
            smoothing_alpha = persistent_number_input(
                "Коэффициент сглаживания alpha",
                key="forecast_smoothing_alpha",
                default=0.35,
                min_value=0.05,
                max_value=0.95,
                step=0.05,
                format="%.2f",
            )
            hidden_units = persistent_number_input(
                "Нейронов в скрытом слое",
                key="forecast_hidden_units",
                default=16,
                min_value=4,
                max_value=64,
                step=4,
            )
        run_clicked = st.button("Запустить прогноз", type="primary", use_container_width=True)
except ApiError as error:
    render_api_error(error)
    st.stop()

if run_clicked:
    validation = validate_common_filters(filters)
    if not validation.ok:
        st.error(validation.message)
    else:
        payload = {
            "station_id": filters["station_id"],
            "parameter_id": filters["parameter_id"],
            "date_from": filters["date_from"].isoformat(),
            "date_to": filters["date_to"].isoformat(),
            "aggregation": filters["aggregation"],
            "model": model,
            "training_mode": training_mode,
            "horizon": int(horizon),
            "horizon_unit": horizon_unit,
            "options": {
                "window": int(model_window),
                "moving_average_window": int(model_window),
                "seasonal_period": int(seasonal_period),
                "alpha": float(smoothing_alpha),
                "lag_window": int(model_window),
                "hidden_units": int(hidden_units),
            },
        }
        try:
            with st.spinner("Клиентский модуль выполняет прогноз..."):
                st.session_state["last_forecast"] = forecasts.run_forecast(payload)
        except ApiError as error:
            render_api_error(error)

result = st.session_state.get("last_forecast")
if not result:
    st.info("Выберите параметры и запустите прогноз.")
    st.stop()

render_timeseries_chart(result.get("forecast") or result.get("values") or result, title="Прогнозные значения")
render_table(result.get("forecast") or result.get("values") or result)

st.subheader("Обучение и проверка модели")
training = result.get("training") if isinstance(result, dict) else None
metrics = result.get("metrics") if isinstance(result, dict) else None
if isinstance(training, dict):
    st.caption(
        f"Режим: {TRAINING_MODES.get(training.get('mode'), training.get('mode'))}; "
        f"точек обучения: {training.get('observations')}."
    )
if isinstance(metrics, dict) and metrics.get("status") == "completed":
    _render_forecast_metrics(metrics)
    _render_forecast_metric_help()
else:
    render_table(metrics, empty_message="Метрики тестовой проверки отсутствуют.")

render_json_preview(result, "Полный JSON прогноза")

