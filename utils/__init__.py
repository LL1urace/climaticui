"""
Модуль утилит для ClimaticUI.
"""

from .data_loader import (
    load_stations,
    load_climate_data,
    get_available_metrics,
    get_station_name,
    get_data_path
)

__all__ = [
    'load_stations',
    'load_climate_data',
    'get_available_metrics',
    'get_station_name',
    'get_data_path'
]
