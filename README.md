# КлиматикА frontend

Streamlit frontend-клиент для backend API системы «КлиматикА».

Приложение не читает локальные CSV, не подключается к PostgreSQL и не выполняет климатические расчёты на клиенте. Все данные, анализы, прогнозы, история и отчёты приходят через backend API.

## Стек

- Python 3.11+
- Streamlit
- httpx
- pandas
- Plotly
- PyDeck
- python-dotenv
- pytest
- Docker

## Конфигурация

Создайте `.env` на основе `.env.example`:

```env
BACKEND_API_URL=http://localhost:8000/api/v1
APP_TITLE=КлиматикА
APP_ENV=dev
REQUEST_TIMEOUT_SECONDS=30
USE_SAMPLE_DATA=true
```

Для запуска frontend в compose рядом с backend-сервисом `api` используйте:

```env
BACKEND_API_URL=http://api:8000/api/v1
USE_SAMPLE_DATA=false
```

`USE_SAMPLE_DATA=true` включает локальный демо-набор данных, совместимый с основными backend-моделями. Это удобно, пока backend ещё не запущен.
Справочник метеостанций sample-режима хранится в SQLite-файле `app/sample/data/klimatika_sample.sqlite`.

## Локальный запуск

```powershell
poetry install
poetry run streamlit run app/main.py
```

Frontend будет доступен на `http://localhost:8501`.

## Docker

```powershell
docker compose up --build
```

Frontend будет доступен на `http://localhost:8501`.

Полезные переменные `.env`:

```env
FRONTEND_PORT=8501
BACKEND_API_URL=http://host.docker.internal:8000/api/v1
USE_SAMPLE_DATA=true
```

По умолчанию Docker-вариант работает в sample-режиме и не требует backend. Для подключения к backend на хосте установите `USE_SAMPLE_DATA=false`.

## Makefile

Если установлен `make`, можно использовать короткие команды:

```powershell
make up-build   # собрать и запустить контейнер
make logs       # смотреть логи frontend
make down       # остановить контейнеры
make test       # запустить pytest внутри контейнера
make local-run  # запустить Streamlit локально
```

## Тесты

```powershell
pytest
```

## Основные страницы

- `app/main.py`: вход, регистрация, статус backend и презентационное описание приложения.
- `app/pages/00_Dashboard.py`: единый выбор периода, метеостанций, карта и переходы к возможностям анализа.
- `app/pages/01_Analysis.py`: запуск основного анализа временного ряда.
- `app/pages/02_Period_Comparison.py`: сравнение двух периодов.
- `app/pages/03_Station_Comparison.py`: сравнение нескольких станций и карта.
- `app/pages/04_Climatogram.py`: температура и осадки по месяцам.
- `app/pages/05_Forecasting.py`: исследовательский прогноз через backend.
- `app/pages/06_Analysis_History.py`: история и открытие результата анализа.
- `app/pages/07_Reports.py`: создание и скачивание отчётов.
- `app/pages/08_Correlation.py`: корреляционный анализ нескольких климатических параметров.

## Backend endpoints

Frontend использует только `/api/v1` endpoints:

- `GET /health`
- `POST /auth/register`
- `POST /auth/login`
- `GET /users/me`
- `GET /climate-zones`
- `GET /stations`
- `GET /parameters`
- `GET /observations/timeseries`
- `GET /observations/availability`
- `POST /analysis/run`
- `GET /analysis/history`
- `GET /analysis/{analysis_run_id}`
- `POST /analysis/correlation`
- `POST /analysis/climatogram`
- `POST /comparisons/periods`
- `POST /comparisons/stations`
- `POST /forecasts/run`
- `POST /reports`
- `GET /reports/{report_id}/download`

