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
```

Для запуска frontend в compose рядом с backend-сервисом `api` используйте:

```env
BACKEND_API_URL=http://api:8000/api/v1
```

## Локальный запуск

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
streamlit run app.py
```

Frontend будет доступен на `http://localhost:8501`.

## Docker

```powershell
docker compose up --build
```

По умолчанию Docker-вариант ожидает backend на хосте: `http://host.docker.internal:8000/api/v1`.

## Тесты

```powershell
pytest
```

## Основные страницы

- `app.py`: вход, регистрация, статус backend, переходы.
- `pages/01_Анализ.py`: запуск основного анализа временного ряда.
- `pages/02_Сравнение_периодов.py`: сравнение двух периодов.
- `pages/03_Сравнение_станций.py`: сравнение нескольких станций и карта.
- `pages/04_Климатограмма.py`: температура и осадки по месяцам.
- `pages/05_Прогнозирование.py`: исследовательский прогноз через backend.
- `pages/06_История_анализов.py`: история и открытие результата анализа.
- `pages/07_Отчёты.py`: создание и скачивание отчётов.

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

