"""Application configuration."""

from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
import os

try:
    from dotenv import load_dotenv
except ImportError:  # pragma: no cover - useful when dotenv is absent in minimal envs
    load_dotenv = None


if load_dotenv:
    load_dotenv()


@dataclass(frozen=True)
class Settings:
    """Хранит настройки frontend-приложения.

    Attributes:
        backend_api_url: Базовый URL backend API.
        app_title: Название приложения в интерфейсе.
        app_env: Название окружения запуска.
        request_timeout_seconds: Таймаут HTTP-запросов в секундах.
        use_sample_data: Флаг использования локального sample API.
    """

    backend_api_url: str = "http://localhost:8000/api/v1"
    app_title: str = "КлиматикА"
    app_env: str = "dev"
    request_timeout_seconds: float = 30.0
    use_sample_data: bool = True

    @property
    def is_dev(self) -> bool:
        """Проверяет, относится ли окружение к development-режиму.

        Returns:
            True, если окружение считается локальным или dev.
        """

        return self.app_env.lower() in {"dev", "local", "development"}


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Создаёт и кэширует настройки приложения из переменных окружения.

    Returns:
        Объект настроек frontend-приложения.
    """

    return Settings(
        backend_api_url=os.getenv("BACKEND_API_URL", "http://localhost:8000/api/v1").rstrip("/"),
        app_title=os.getenv("APP_TITLE", "КлиматикА"),
        app_env=os.getenv("APP_ENV", "dev"),
        request_timeout_seconds=float(os.getenv("REQUEST_TIMEOUT_SECONDS", "30")),
        use_sample_data=os.getenv("USE_SAMPLE_DATA", "true").lower() in {"1", "true", "yes", "on"},
    )

