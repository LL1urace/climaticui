# ClimaticUI - Context Documentation

## Project Overview

**ClimaticUI** is a Streamlit-based web application for analyzing and visualizing climate/meteorological data for the Eurasia region. The application provides tools for data exploration, mapping, analytics, forecasting, and report generation.

### Key Features

- **Authentication System** - User registration, login, session management with bcrypt password hashing
- **Dashboard** - KPI metrics and climate data overview
- **Interactive Map** - Weather station locations with Plotly geo-maps
- **Analytics** - Time series analysis, correlation matrices, period comparison
- **Forecasting** - Predictive modeling with confidence intervals
- **Reports** - CSV/TXT export and summary report generation

### Tech Stack

- **Framework:** Streamlit (>=1.55.0)
- **Language:** Python 3.12+
- **Data Processing:** Pandas, NumPy
- **Visualization:** Plotly, Matplotlib
- **Security:** bcrypt for password hashing
- **Package Manager:** Poetry

## Project Structure

```
ClimaticUI/
├── app.py                      # Main application entry point
├── pyproject.toml              # Poetry dependencies & project config
├── .env                        # Environment variables (create from .env-example)
├── .streamlit/
│   └── config.toml             # Streamlit theme & server config
│
├── app/                        # Application components
│   ├── components/
│   │   └── navbar.py           # Navigation bar component
│   └── styles.css              # Custom CSS (purple-white theme)
│
├── pages/                      # Streamlit multi-page app
│   ├── 0_Login.py              # Login page
│   ├── 1_Dashboard.py          # Main dashboard with KPIs
│   ├── 2_Map_View.py           # Interactive weather station map
│   ├── 3_Analysis.py           # Analysis hub (menu page)
│   ├── 3_Analytics.py          # Time series & correlation analysis
│   ├── 4_Forecast.py           # Climate forecasting
│   ├── 5_Reports.py            # Report generation & export
│   ├── Profile.py              # User profile management
│   └── Register.py             # User registration
│
├── utils/                      # Utility modules
│   ├── auth.py                 # Authentication logic (bcrypt, user CRUD)
│   ├── auth_session.py         # Session management & cookies
│   ├── auth_check.py           # Authorization helpers
│   ├── data_loader.py          # CSV data loading with caching
│   └── session.py              # Session state utilities
│
└── data/                       # Data files (CSV)
    ├── users.csv               # User credentials (auto-created)
    ├── stations_coordinates.csv # Weather station metadata
    └── climate_data_sample.csv  # Climate observations
```

## Building and Running

### Prerequisites

- Python 3.12 or higher
- Poetry package manager

### Installation

```bash
# Clone/navigate to project
cd ClimaticUI

# Install dependencies
poetry install

# Copy environment file
cp .env-example .env
```

### Running the Application

```bash
# Start Streamlit server
poetry run streamlit run app.py

# Or with specific config
poetry run streamlit run app.py --server.port 8501 --server.address localhost
```

### Default Test Accounts

| Username | Email | Password |
|----------|-------|----------|
| admin | admin@climatic.ui | password123 |
| testuser | test@test.com | password123 |
| meteorolog | meteorolog@climatic.ui | password123 |
| analyst | analyst@climatic.ui | password123 |

## Configuration

### Environment Variables (.env)

```ini
APP_NAME=ClimaticUI
APP_ENV=development
DEBUG=True

STREAMLIT_SERVER_PORT=8501
STREAMLIT_SERVER_ADDRESS=localhost

SECRET_KEY=your-secret-key-change-in-production
```

### Streamlit Config (.streamlit/config.toml)

```toml
[theme]
primaryColor = "#7c3aed"        # Purple theme
backgroundColor = "#ffffff"
secondaryBackgroundColor = "#f5f3ff"
textColor = "#1f2937"
font = "sans serif"

[server]
headless = true
port = 8501
enableCORS = false
enableXsrfProtection = true
```

## Data Model

### Users (`data/users.csv`)
- `id`, `username`, `email`, `password_hash`, `full_name`, `created_at`

### Weather Stations (`data/stations_coordinates.csv`)
- `station_id`, `name`, `latitude`, `longitude`, `region`, `elevation_m`

### Climate Data (`data/climate_data_sample.csv`)
- `date`, `station_id`, `temperature_c`, `humidity_pct`, `pressure_hpa`, `wind_speed_ms`, `precipitation_mm`

## Development Conventions

### Code Style
- **Docstrings:** Google-style for all public functions
- **Type Hints:** Used throughout (Optional, Tuple, List, dict)
- **Naming:** snake_case for functions/variables, PascalCase for classes

### Architecture Patterns
- **Multi-page App:** Streamlit's `pages/` convention for routing
- **Session State:** Centralized state management via `utils/auth_session.py`
- **Caching:** `@st.cache_data` for expensive data loading operations
- **Component-based UI:** Reusable components in `app/components/`

### Security Practices
- Passwords hashed with bcrypt before storage
- Session tokens via MD5 hash with salt
- Cookie-based session persistence
- CSRF protection enabled in Streamlit config

### Testing Practices
- Manual testing via UI (no automated tests currently)
- Test accounts provided for QA
- Data validation in loaders (required columns check)

## Key Modules

### `utils/auth.py`
Core authentication functions:
- `authenticate_user(username, password)` - Login validation
- `register_user(username, email, password, full_name)` - User creation
- `hash_password(password)` / `verify_password(password, hash)` - Password utilities
- `get_user_by_id(user_id)` - User lookup

### `utils/data_loader.py`
Data access with Streamlit caching:
- `load_stations()` - Cached station metadata
- `load_climate_data()` - Cached climate observations
- `get_available_metrics()` - Metric definitions
- `get_station_name(stations_df, station_id)` - Station lookup

### `app/components/navbar.py`
Navigation component:
- Custom purple gradient navbar
- Conditional rendering (auth/unauth)
- User info display in header

## Common Tasks

### Add New Page
1. Create file in `pages/` with naming pattern `N_Page_Name.py`
2. Add to navbar in `app/components/navbar.py`
3. Use standard lifecycle: `set_page_config` → `init_session_state` → `require_auth`

### Add New Metric
1. Update `get_available_metrics()` in `utils/data_loader.py`
2. Add to sidebar filters in relevant pages
3. Update visualization components

### Change Theme Colors
Edit `.streamlit/config.toml` and `app/styles.css`

## Troubleshooting

### Session Issues
- Clear browser cookies
- Check `SECRET_KEY` in `.env`
- Restart Streamlit server

### Data Loading Errors
- Verify CSV files exist in `data/`
- Check column names match expected schema
- Ensure files are not empty/corrupted

### Port Already in Use
```bash
# Change port in .env or run with different port
poetry run streamlit run app.py --server.port 8502
```

## Version

- **Current:** 0.1.0
- **Python:** >=3.12
- **Streamlit:** >=1.55.0,<2.0.0
