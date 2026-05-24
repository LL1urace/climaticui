"""HTTP client and error normalization for the backend API."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable

import httpx


@dataclass
class ApiError(Exception):
    """Описывает нормализованную ошибку backend API.

    Attributes:
        message: Пользовательское сообщение об ошибке.
        status_code: HTTP-статус ответа, если он известен.
        code: Машинный код ошибки backend.
        context: Дополнительный контекст ошибки.
        raw: Исходный ответ backend или его часть.
    """

    message: str
    status_code: int | None = None
    code: str | None = None
    context: dict[str, Any] = field(default_factory=dict)
    raw: Any = None

    def __str__(self) -> str:
        """Формирует строковое представление ошибки.

        Returns:
            Сообщение ошибки с кодом, если он указан.
        """

        prefix = f"{self.code}: " if self.code else ""
        return f"{prefix}{self.message}"


class ApiClient:
    """Выполняет HTTP-запросы к backend API и нормализует ошибки.

    Attributes:
        base_url: Базовый URL backend API.
        token: JWT-токен для защищённых запросов.
        timeout: Таймаут HTTP-запроса в секундах.
        transport: Транспорт httpx, используемый в тестах.
        on_unauthorized: Callback для обработки ответа 401.
    """

    def __init__(
        self,
        base_url: str,
        token: str | None = None,
        timeout: float = 30.0,
        transport: httpx.BaseTransport | None = None,
        on_unauthorized: Callable[[], None] | None = None,
    ) -> None:
        """Инициализирует API-клиент.

        Args:
            base_url: Базовый URL backend API.
            token: JWT-токен пользователя.
            timeout: Таймаут HTTP-запросов в секундах.
            transport: Пользовательский транспорт httpx.
            on_unauthorized: Callback при HTTP 401.

        Returns:
            None.
        """

        self.base_url = base_url.rstrip("/")
        self.token = token
        self.timeout = timeout
        self.transport = transport
        self.on_unauthorized = on_unauthorized

    def get(self, path: str, params: dict[str, Any] | None = None) -> Any:
        """Выполняет GET-запрос к backend API.

        Args:
            path: Путь endpoint относительно `base_url`.
            params: Query-параметры запроса.

        Returns:
            Распарсенный JSON-ответ backend.

        Raises:
            ApiError: Если запрос завершился ошибкой.
        """

        return self._request("GET", path, params=params)

    def post(self, path: str, json: dict[str, Any] | None = None) -> Any:
        """Выполняет POST-запрос к backend API.

        Args:
            path: Путь endpoint относительно `base_url`.
            json: JSON-тело запроса.

        Returns:
            Распарсенный JSON-ответ backend.

        Raises:
            ApiError: Если запрос завершился ошибкой.
        """

        return self._request("POST", path, json=json)

    def download(self, path: str, params: dict[str, Any] | None = None) -> bytes:
        """Скачивает бинарный ответ backend API.

        Args:
            path: Путь endpoint относительно `base_url`.
            params: Query-параметры запроса.

        Returns:
            Содержимое ответа в байтах.

        Raises:
            ApiError: Если запрос завершился ошибкой.
        """

        return self._request("GET", path, params=params, expect_bytes=True)

    def _request(
        self,
        method: str,
        path: str,
        params: dict[str, Any] | None = None,
        json: dict[str, Any] | None = None,
        expect_bytes: bool = False,
    ) -> Any:
        """Выполняет HTTP-запрос и приводит ответ к JSON или bytes.

        Args:
            method: HTTP-метод.
            path: Путь endpoint относительно `base_url`.
            params: Query-параметры запроса.
            json: JSON-тело запроса.
            expect_bytes: Нужно ли вернуть ответ как bytes.

        Returns:
            JSON-ответ backend или байты файла.

        Raises:
            ApiError: Если backend недоступен, вернул ошибку или невалидный JSON.
        """

        try:
            with httpx.Client(timeout=self.timeout, transport=self.transport) as client:
                response = client.request(
                    method,
                    self._url(path),
                    params=params,
                    json=json,
                    headers=self._headers(),
                )
        except httpx.TimeoutException as exc:
            raise ApiError("Backend не ответил вовремя. Попробуйте повторить запрос.", code="TIMEOUT") from exc
        except httpx.RequestError as exc:
            raise ApiError("Не удалось подключиться к backend API.", code="CONNECTION_ERROR", context={"error": str(exc)}) from exc

        if response.status_code == 401 and self.on_unauthorized:
            self.on_unauthorized()

        if response.is_error:
            raise self._api_error_from_response(response)

        if expect_bytes:
            return response.content

        if response.status_code == 204 or not response.content:
            return {}

        try:
            return response.json()
        except ValueError as exc:
            raise ApiError(
                "Backend вернул ответ в неподдерживаемом формате.",
                status_code=response.status_code,
                code="INVALID_RESPONSE",
                raw=response.text,
            ) from exc

    def _headers(self) -> dict[str, str]:
        """Создаёт HTTP-заголовки для запроса.

        Returns:
            Словарь HTTP-заголовков с JWT, если токен задан.
        """

        headers = {"Accept": "application/json"}
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"
        return headers

    def _url(self, path: str) -> str:
        """Собирает абсолютный URL endpoint.

        Args:
            path: Путь endpoint относительно `base_url`.

        Returns:
            Абсолютный URL для HTTP-запроса.
        """

        clean_path = path if path.startswith("/") else f"/{path}"
        return f"{self.base_url}{clean_path}"

    @staticmethod
    def _api_error_from_response(response: httpx.Response) -> ApiError:
        """Преобразует HTTP-ошибку backend в `ApiError`.

        Args:
            response: Ответ httpx с ошибочным HTTP-статусом.

        Returns:
            Нормализованная ошибка API.
        """

        try:
            payload = response.json()
        except ValueError:
            return ApiError(
                "Backend вернул ошибку без JSON-описания.",
                status_code=response.status_code,
                code=f"HTTP_{response.status_code}",
                raw=response.text,
            )

        detail = payload.get("detail") if isinstance(payload, dict) else None
        if isinstance(detail, dict):
            return ApiError(
                message=detail.get("message") or "Backend вернул ошибку.",
                status_code=response.status_code,
                code=detail.get("code") or f"HTTP_{response.status_code}",
                context=detail.get("context") or {},
                raw=payload,
            )

        if isinstance(detail, str):
            message = detail
        else:
            message = payload.get("message") if isinstance(payload, dict) else None

        return ApiError(
            message=message or "Backend вернул ошибку.",
            status_code=response.status_code,
            code=f"HTTP_{response.status_code}",
            raw=payload,
        )

