"""Auth endpoints."""

from __future__ import annotations

from klimatika_frontend.api import get_api_client


def register(email: str, password: str, full_name: str) -> dict:
    """Регистрирует пользователя через backend API.

    Args:
        email: Email пользователя.
        password: Пароль пользователя.
        full_name: Полное имя пользователя.

    Returns:
        JSON-ответ с данными зарегистрированного пользователя.

    Raises:
        ApiError: Если регистрация отклонена backend API.
    """

    return get_api_client().post("/auth/register", json={"email": email, "password": password, "full_name": full_name})


def login(email: str, password: str) -> dict:
    """Выполняет вход пользователя через backend API.

    Args:
        email: Email пользователя.
        password: Пароль пользователя.

    Returns:
        JSON-ответ с JWT-токеном.

    Raises:
        ApiError: Если данные входа неверны или backend недоступен.
    """

    return get_api_client().post("/auth/login", json={"email": email, "password": password})


def get_current_user() -> dict:
    """Получает профиль текущего пользователя по JWT.

    Returns:
        JSON-ответ с данными текущего пользователя.

    Raises:
        ApiError: Если токен недействителен или backend вернул ошибку.
    """

    return get_api_client().get("/users/me")

