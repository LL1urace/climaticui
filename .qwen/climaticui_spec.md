# Project Specification: ClimaticUI (Frontend)

**Document Version:** 1.0  
**Last Updated:** May 24, 2024  
**Status:** Draft / In Development  

---

## 1. Introduction

### 1.1. System Purpose
**ClimaticUI** represents the client-side component of a distributed climate data analysis system. Its main purpose is to provide an intuitive interface for researchers and analysts to visualize meteorological indicators, interact with the backend service (ClimaticAPI), and generate final reports.

### 1.2. Scope of Application
The system is designed to work with historical and forecast data for the Eurasia region. It allows tracking the dynamics of climate variables, identifying anomalies, and exporting results for further processing.

### 1.3. Architecture Limitations
At the current stage of project development, **no full-fledged DBMS is used**. Storage of configuration data, weather station directories, and test datasets is handled via the file system (`.csv`, `.xlsx` formats). Dynamic data is loaded through the API or emulated via local files for testing purposes.

---

## 2. Technology Stack

To implement the interface, tools have been selected that ensure rapid development, rich visualization, and client-side data processing.

| Component | Technology | Version (rec.) | Purpose |
| :--- | :--- | :--- | :--- |
| **Programming Language** | Python | 3.9+ | Core application logic |
| **UI Framework** | Streamlit | Latest | Web interface creation without HTML/CSS |
| **Visualization (2D/3D)** | Plotly | Latest | Interactive charts and diagrams |
| **Cartography** | Cartopy / Plotly Geo | Latest | Rendering Eurasia maps with data overlays |
| **Data Processing** | Pandas | Latest | Table manipulation, aggregation, filtering |
| **HTTP Client** | Requests / HTTPX | Latest | Interaction with ClimaticAPI |
| **State Management** | Streamlit Session State | Built-in | Caching user session parameters |
| **File Data** | CSV / Excel | N/A | Storage of directories and test datasets |

---

## 3. Functional Requirements

### 3.1. Core Modules

| ID | Module | Functionality Description |
| :--- | :--- | :--- |
| **F-01** | **Request Configurator** | Input form for parameters: selection of geographic region (polygon or station list), time range (start/end date), list of metrics (temperature, humidity, etc.). |
| **F-02** | **API Client** | Formation and submission of asynchronous HTTP requests to ClimaticAPI service. Handling timeouts and connection errors. |
| **F-03** | **Task Monitoring** | Visualization of data loading process: progress bars, activity indicators (spinners), success notifications. |
| **F-04** | **Data Visualization** | Rendering maps with stations, time series, anomaly heatmaps. Support for zooming and cursor hover (tooltips). |
| **F-05** | **Interactivity** | Ability to filter charts by legend, zoom maps, highlight specific periods on the time axis. |
| **F-06** | **Data Export** | Generation of downloadable files: chart screenshots (`.png`), raw data (`.csv`), summary reports (`.pdf`). |
| **F-07** | **Session Management** | Preservation of selected filters and interface state during accidental page refresh (within a single browser session). |

---

## 4. Interface Structure (Navigation)

The application is built on a modular principle with sidebar or top navigation.

1.  **📊 Dashboard (Main)**
    *   Summary metrics (average temperature, number of stations in selection).
    *   Quick links to recent reports.
    *   API connection status.
2.  **🗺️ Map View**
    *   Interactive Eurasia map.
    *   Display of weather station clusters.
    *   Color coding of stations by current indicators.
3.  **📈 Analytics**
    *   Time series plotting.
    *   Period comparison (e.g., 2023 vs 2024).
    *   Correlation analysis of variables.
4.  **🔮 Forecast**
    *   Visualization of machine learning model results.
    *   Forecast reliability assessment.
5.  **📑 Reports**
    *   Report builder.
    *   History of generated files.
    *   Download buttons.

---

## 5. Data Specification (File Storage)

Due to the absence of a database, the system relies on local files for reference information and testing. Below are the file structures that should be located in the project's `/data` folder.

### 5.1. Weather Station Directory (`stations_coordinates.csv`)
Contains geographic bindings of station identifiers.

```csv
station_id,name,latitude,longitude,region,elevation_m
RU-001,Moscow (VDNKh),55.8263,37.6365,Central,150
RU-002,Saint Petersburg,59.9343,30.3351,North-West,3
KZ-001,Almaty,43.2567,76.9286,Central Asia,760
CN-001,Beijing,39.9042,116.4074,East Asia,43
JP-001,Tokyo,35.6762,139.6503,East Asia,40
```

### 5.2. Test Climate Data (`climate_data_sample.csv`)
Emulates API response for visualization debugging. Contains time series.

```csv
date,station_id,temperature_c,humidity_pct,pressure_hpa,wind_speed_ms,precipitation_mm
2023-01-01,RU-001,-5.2,78,1015.3,4.5,0.0
2023-01-01,RU-002,-2.1,85,1010.1,6.2,1.5
2023-01-01,KZ-001,-1.5,60,1020.5,2.1,0.0
2023-01-02,RU-001,-6.0,80,1014.8,5.0,0.5
2023-01-02,RU-002,-3.5,82,1009.5,7.1,2.0
2023-01-02,KZ-001,-2.0,62,1019.9,2.5,0.0
2023-01-03,RU-001,-4.5,75,1016.0,3.8,0.0
2023-01-03,CN-001,2.5,45,1025.0,1.5,0.0
2023-01-03,JP-001,8.5,70,1012.0,5.5,5.0
```

> **Note:** For use in the project, save the table contents above to files with `.csv` extension in `UTF-8` encoding. These files will be loaded via `pandas.read_csv()` at application startup for directory initialization.

---

## 6. Performance and Security Requirements

1.  **Response Time:** The interface should remain responsive when loading datasets up to 10,000 rows.
2.  **Error Handling:** When ClimaticAPI is unavailable, the user should receive a clear error message, not a stack trace.
3.  **Validation:** Input data (dates, coordinates) must be validated for correctness before sending requests.
4.  **Caching:** Results of heavy requests should be cached within the session (`st.cache_data`) to avoid repeated requests when changing other UI parameters.

---

## 7. Launch Plan (Local Development)

1.  Install dependencies:
    ```bash
    pip install streamlit plotly pandas cartopy requests openpyxl
    ```
2.  Create `data` directory and place test files there (`stations_coordinates.csv`, `climate_data_sample.csv`).
3.  Launch the application:
    ```bash
    streamlit run app.py
    ```

---
*This document is an internal specification guide for the ClimaticUI development team.*