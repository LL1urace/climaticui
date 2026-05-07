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
    backend_api_url: str = "http://localhost:8000/api/v1"
    app_title: str = "КлиматикА"
    app_env: str = "dev"
    request_timeout_seconds: float = 30.0

    @property
    def is_dev(self) -> bool:
        return self.app_env.lower() in {"dev", "local", "development"}


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings(
        backend_api_url=os.getenv("BACKEND_API_URL", "http://localhost:8000/api/v1").rstrip("/"),
        app_title=os.getenv("APP_TITLE", "КлиматикА"),
        app_env=os.getenv("APP_ENV", "dev"),
        request_timeout_seconds=float(os.getenv("REQUEST_TIMEOUT_SECONDS", "30")),
    )

